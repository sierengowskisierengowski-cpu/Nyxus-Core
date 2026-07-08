// NYXUS Filter · NOIR — full DARK MIRROR desaturation with a cold
// blue-steel tint and lifted contrast. The whole desktop goes film-noir.
// © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 c = texture(tex, v_texcoord);
    float lum = dot(c.rgb, vec3(0.299, 0.587, 0.114));
    // s-curve contrast
    lum = smoothstep(0.04, 0.96, lum);
    // cold steel tint
    c.rgb = lum * vec3(0.92, 0.97, 1.06);
    fragColor = c;
}
