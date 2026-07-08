// NYXUS Filter · VIGNETTE — cinematic edge falloff, deepens the
// frosted-glass look without touching the center of the screen.
// © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 c = texture(tex, v_texcoord);
    vec2 d = v_texcoord - vec2(0.5);
    // smooth radial falloff: full brightness inside r=0.55, -35% at corners
    float vig = 1.0 - 0.35 * smoothstep(0.55, 0.95, length(d) * 1.4142);
    c.rgb *= vig;
    fragColor = c;
}
