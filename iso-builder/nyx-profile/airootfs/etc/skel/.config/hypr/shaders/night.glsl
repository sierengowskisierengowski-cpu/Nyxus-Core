// NYXUS Filter · NIGHT — warm color temperature for late sessions.
// © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 c = texture(tex, v_texcoord);
    // ~3800K shift: keep red, pull green a touch, pull blue hard
    c.rgb *= vec3(1.00, 0.86, 0.62);
    fragColor = c;
}
