#include std_head_vs.inc

varying vec2 texcoordoutf;
varying vec2 texcoordoutb;

void main(void) {
  // Foreground
  vec2 scale_f = unif[14].xy;
  vec2 offset_f = unif[16].xy;
  texcoordoutf = texcoord / scale_f + (0.5 - 0.5 / scale_f) - offset_f;
  
  // Background
  vec2 scale_b = unif[15].xy;
  vec2 offset_b = vec2(unif[16].z, unif[17].x);
  texcoordoutb = texcoord / scale_b + (0.5 - 0.5 / scale_b) - offset_b;

  gl_Position = modelviewmatrix[1] * vec4(vertex,1.0);
  dist = gl_Position.z;
  gl_PointSize = unib[2][2] / dist;
}