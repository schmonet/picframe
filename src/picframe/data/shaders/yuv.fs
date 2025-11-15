#version 100

precision mediump float;

uniform sampler2D s_texture_y; // Y plane
uniform sampler2D s_texture_u; // U plane
uniform sampler2D s_texture_v; // V plane

varying vec2 v_texcoord;

void main(void) {
    // Sample Y, U, and V components
    float y = texture2D(s_texture_y, v_texcoord).r;
    float u = texture2D(s_texture_u, v_texcoord).r;
    float v = texture2D(s_texture_v, v_texcoord).r;

    // Adjust U and V to be centered around 0
    u = u - 0.5;
    v = v - 0.5;

    // YUV to RGB conversion matrix (BT.601 standard)
    vec3 rgb;
    rgb.r = y + 1.402 * v;
    rgb.g = y - 0.344 * u - 0.714 * v;
    rgb.b = y + 1.772 * u;

    gl_FragColor = vec4(rgb, 1.0);
}
