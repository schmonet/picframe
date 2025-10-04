// ----- boiler-plate code for vertex shader variable definition
#version 120

attribute vec3 vertex;
attribute vec3 normal;
attribute vec2 texcoord;

uniform mat4 modelviewmatrix[3];
uniform vec3 unib[5];
uniform vec3 unif[20];

varying float dist;
varying float fog_start;
varying float is_3d;

// End of std_head_vs.inc

varying vec2 texcoordoutf;
varying vec2 texcoordoutb;

void main(void) {
  // unif mapping from viewer_display.py:
  // unif[14].x -> unif[42]
  // unif[14].y -> unif[43]
  // unif[14].z -> unif[44] (alpha)
  // unif[15].x -> unif[45]
  // unif[15].y -> unif[46]
  // unif[16].x -> unif[48]
  // unif[16].y -> unif[49]
  // unif[16].z -> unif[50]
  // unif[17].x -> unif[51]

  // Foreground
  vec2 scale_f = vec2(unif[14].x, unif[14].y);
  vec2 offset_f = vec2(unif[16].x, unif[16].y);
  texcoordoutf = (texcoord - 0.5) / scale_f + 0.5 - offset_f;
  
  // Background
  vec2 scale_b = vec2(unif[15].x, unif[15].y);
  vec2 offset_b = vec2(unif[16].z, unif[17].x);
  texcoordoutb = (texcoord - 0.5) / scale_b + 0.5 - offset_b;

  gl_Position = modelviewmatrix[1] * vec4(vertex,1.0);
  dist = gl_Position.z;
  gl_PointSize = unib[2][2] / dist;
}
