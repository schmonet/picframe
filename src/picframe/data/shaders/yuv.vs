#version 100

attribute vec3 vertex;
attribute vec2 texcoord;

uniform mat4 modelviewmatrix;
uniform mat4 projmatrix;

varying vec2 v_texcoord;

void main(void) {
    gl_Position = projmatrix * modelviewmatrix * vec4(vertex, 1.0);
    v_texcoord = texcoord;
}
