// NYXUS Filter · EMBER — comet-fire glow. Warm white-balance shift,
// saturation lift weighted toward the fire hues, and a soft highlight
// bloom so neon and the comet ring smolder instead of glare. Subtle by
// design: ~4% color shift at the midtones, stronger only where the
// frame is already bright.
// Part of the nyxus-shader cycle (Super+O) · Super+Ctrl+O jumps here.
// © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 c = texture(tex, v_texcoord);

    // warm the white point: nudge red up, blue down (≈3800K whisper)
    c.rgb *= vec3(1.035, 1.0, 0.955);

    // vibrance: boost saturation more on muted pixels, spare skin/neon
    float luma = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
    float sat  = max(max(c.r, c.g), c.b) - min(min(c.r, c.g), c.b);
    c.rgb = mix(vec3(luma), c.rgb, 1.0 + 0.22 * (1.0 - sat));

    // ember glow: highlights bleed a touch of gold, shadows stay void
    float hi = smoothstep(0.62, 1.0, luma);
    c.rgb += hi * hi * vec3(0.055, 0.030, 0.0);

    // keep the void black: gently deepen the darkest 8%
    float lo = smoothstep(0.08, 0.0, luma);
    c.rgb *= 1.0 - 0.10 * lo;

    fragColor = vec4(clamp(c.rgb, 0.0, 1.0), c.a);
}
