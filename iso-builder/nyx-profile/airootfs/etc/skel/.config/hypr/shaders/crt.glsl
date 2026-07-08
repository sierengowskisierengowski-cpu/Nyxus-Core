// NYXUS Filter · CRT — scanlines + mild chromatic aberration + vignette.
// Built for the emulation workspace: subtle enough to leave on.
// © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec2 uv = v_texcoord;

    // mild horizontal chromatic aberration (stronger toward edges)
    float ab = 0.0012 * (abs(uv.x - 0.5) * 2.0 + 0.35);
    float r = texture(tex, uv + vec2(ab, 0.0)).r;
    float g = texture(tex, uv).g;
    float b = texture(tex, uv - vec2(ab, 0.0)).b;
    vec3 c = vec3(r, g, b);

    // scanlines — every other physical-ish line, gentle 12% dip
    float line = sin(uv.y * 1080.0 * 3.14159);
    c *= 1.0 - 0.12 * (0.5 + 0.5 * line);

    // phosphor-style slight saturation lift
    float lum = dot(c, vec3(0.299, 0.587, 0.114));
    c = mix(vec3(lum), c, 1.12);

    // corner vignette
    vec2 d = v_texcoord - vec2(0.5);
    c *= 1.0 - 0.30 * smoothstep(0.5, 1.0, length(d) * 1.4142);

    fragColor = vec4(c, 1.0);
}
