/** @resolution */
uniform vec2 u_resolution;

/** @default 0.35 */
uniform float u_opacity;

/** @default 40.0 */
uniform float u_scale;

/** @color @default #4A6B52 */
uniform vec3 u_color;

void main() {
  vec2 uv = gl_FragCoord.xy / u_scale;
  float lineX = smoothstep(0.0, 0.06, abs(fract(uv.x) - 0.5));
  float lineY = smoothstep(0.0, 0.06, abs(fract(uv.y) - 0.5));
  float weave = min(lineX, lineY);
  float diag1 = smoothstep(0.0, 0.08, abs(fract(uv.x + uv.y) - 0.5));
  float diag2 = smoothstep(0.0, 0.08, abs(fract(uv.x - uv.y) - 0.5));
  float pattern = min(weave, min(diag1, diag2));
  float alpha = (1.0 - pattern) * u_opacity;
  gl_FragColor = vec4(u_color, alpha);
}
