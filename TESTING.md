# Picframe Testing & Performance Results

This document contains various test results and performance analyses conducted on the target hardware.

## Video Player Comparison

This table summarizes the results of testing different command-line video players on the target system.

| Player | Result | Notes |
| :--- | :--- | :--- |
| **mpv** | Plays correctly, exits cleanly. | Shows some warnings on console (`[vo/sdl] Warning: this legacy VO has bad performance...`). Returns to console after playback. Seems to be the most promising candidate for integration. |
| **vlc** | Plays correctly, but hangs at the end. | Requires `Ctrl-C` to exit. Uses DRM Video Accel for hardware decoding. |
| **ffplay** | Plays correctly, but hangs at the end. | Last frame remains on screen. Requires `Ctrl-C` to exit. |
| **mplayer** | Fails to play. | Error: `vo: couldn't open the X11 display ()!`. Cannot initialize video driver. |

## Video Playback Test Results

### Display Properties

- **Hersteller:** `Sony`
- **Modell:** `SONY TV`
- **Baujahr:** `2014`
- **DRM_Connector:** `HDMI-A-1`
- **Display:** `HDMI-A-1`
- **Auflösung:** `1920x1080`
- **Bildwiederholrate:** `50.00 Hz`

--- Test results for Sony KDL-32W705B ---
| Verzeichnis | Videodatei | Auflösung | Codec | Profile@Level | MP4/FPS | Dauer | Frames | Status | Laufzeit | Playback | Performance | MPV/FPS | Display/FPS | Details |
|-------------|------------|-----------|-------|---------------|---------|--------|--------|--------|----------|----------|-------------|---------|-------------|---------|
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.avi | 1280x720 | h264 | High@3.2 | 600.00 | 9.98s | 452 | OK | 15.18s | 9.99s | OK | 45.2 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mkv | 1280x720 | h264 | High@3.2 | 50.00 | 0.00s | 452 | OK | 13.03s | 9.02s | OK | 50.1 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mov | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.76s | 9.00s | OK | 50.2 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.91s | 8.99s | OK | 50.3 | 0.00 |  |
| ext | Super8.mp4 | 960x720 | h264 | High@3.1 | 18.00 | 19.11s | 344 | OK | 22.78s | 19.02s | OK | 18.1 | 0.00 |  |
| hd | 1280x720p25_2ch_libx264_high_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 14.34s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1280x720p25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.96s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1280x720p25_2ch_libx265_main_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@9.3 | 25.00 | 10.08s | 252 | OK | 14.03s | 10.21s | OK | 24.7 | 0.00 |  |
| hd | 1280x720p25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@9.3 | 25.00 | 10.08s | 252 | OK | 14.36s | 10.31s | OK | 24.4 | 0.00 |  |
| hd | 1280x720p50_2ch_libx264_high_yuv420p_gop100_bit3584k_max3584k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.81s | 10.03s | OK | 50.0 | 0.00 |  |
| hd | 1280x720p50_2ch_libx264_high_yuv420p_gop100_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.79s | 10.04s | OK | 50.0 | 0.00 |  |
| hd | 1280x720p50_2ch_libx265_main_yuv420p_gop100_bit3584k_max3584k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 14.86s | 10.88s | OK | 46.1 | 0.00 |  |
| hd | 1280x720p50_2ch_libx265_main_yuv420p_gop100_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 14.95s | 10.98s | OK | 45.7 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx264_high_yuv420p_gop50_bit3584k_max3584k_buf6M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.2 | 25.00 | 10.08s | 252 | OK | 13.99s | 10.08s | OK | 25.0 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.2 | 25.00 | 10.08s | 252 | OK | 14.13s | 10.15s | OK | 24.8 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx265_main_yuv420p_gop50_bit3584k_max3584k_buf6M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 14.72s | 10.58s | OK | 23.8 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 15.05s | 10.64s | OK | 23.7 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx264_high_yuv420p_gop50_bit3584k_max3584k_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.0 | 25.00 | 10.08s | 252 | OK | 14.26s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.0 | 25.00 | 10.08s | 252 | OK | 14.30s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx265_main_yuv420p_gop50_bit3584k_max3584k_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 14.64s | 10.48s | OK | 24.0 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 15.02s | 10.57s | OK | 23.8 | 0.00 |  |
| hd | 320x180p12_2ch_libx264_baseline_yuv420p_gop25_bit128k_max128k_buf256k_lcaac_56k_48k_2ch_eng.mp4 | 320x180 | h264 | High@1.2 | 12.00 | 10.17s | 122 | OK | 13.86s | 10.05s | OK | 12.1 | 0.00 |  |
| hd | 320x180p12_2ch_libx265_baseline_yuv420p_gop25_bit128k_max128k_buf256k_lcaac_56k_48k_2ch_eng.mp4 | 320x180 | hevc | Main@6.0 | 12.00 | 10.17s | 122 | OK | 13.76s | 10.05s | OK | 12.1 | 0.00 |  |
| hd | 480x270p25_2ch_libx264_baseline_yuv420p_gop50_bit256k_max256k_buf512k_lcaac_64k_48k_2ch_eng.mp4 | 480x270 | h264 | High@2.1 | 25.00 | 10.08s | 252 | OK | 13.72s | 10.02s | OK | 25.1 | 0.00 |  |
| hd | 480x270p25_2ch_libx265_baseline_yuv420p_gop50_bit256k_max256k_buf512k_lcaac_64k_48k_2ch_eng.mp4 | 480x270 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.73s | 10.07s | OK | 25.0 | 0.00 |  |
| hd | 512x288p25_2ch_libx264_main_yuv420p_gop50_bit512k_max512k_buf1024k_lcaac_96k_48k_2ch_eng.mp4 | 512x288 | h264 | High@2.1 | 25.00 | 10.08s | 252 | OK | 13.71s | 10.07s | OK | 25.0 | 0.00 |  |
| hd | 512x288p25_2ch_libx265_main_yuv420p_gop50_bit512k_max512k_buf1024k_lcaac_96k_48k_2ch_eng.mp4 | 512x288 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.90s | 10.16s | OK | 24.8 | 0.00 |  |
| hd | 640x360p25_2ch_libx264_main_yuv420p_gop50_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x360 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.69s | 10.01s | OK | 25.2 | 0.00 |  |
| hd | 640x360p25_2ch_libx265_main_yuv420p_gop50_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x360 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.83s | 10.11s | OK | 24.9 | 0.00 |  |
| hd | 640x720p50_2ch_libx264_high_yuv420p_gop100_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x720 | h264 | High@3.1 | 50.00 | 10.04s | 502 | OK | 13.76s | 10.05s | OK | 50.0 | 0.00 |  |
| hd | 640x720p50_2ch_libx265_main_yuv420p_gop100_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x720 | hevc | Main@9.3 | 50.00 | 10.04s | 502 | OK | 13.82s | 10.00s | OK | 50.2 | 0.00 |  |
| hd | 720x576i25_2ch_libx264_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.85s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576i25_2ch_libx265_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 14.01s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576p25_2ch_libx264_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.92s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576p25_2ch_libx265_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 13.88s | 10.15s | OK | 24.8 | 0.00 |  |
| hd | 960x540p25_2ch_libx264_main_yuv420p_gop50_bit1800k_max1800k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.81s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p25_2ch_libx264_main_yuv420p_gop50_bit2500k_max2500k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.87s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p25_2ch_libx265_main_yuv420p_gop50_bit1800k_max1800k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 14.00s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p50_2ch_libx264_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 50.00 | 10.04s | 502 | OK | 13.72s | 10.02s | OK | 50.1 | 0.00 |  |
| hd | 960x540p50_2ch_libx265_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | hevc | Main@9.3 | 50.00 | 10.04s | 502 | OK | 13.81s | 10.05s | OK | 50.0 | 0.00 |  |
| hd | 960x720p50_2ch_libx264_high_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.84s | 10.02s | OK | 50.1 | 0.00 |  |
| hd | 960x720p50_2ch_libx265_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 13.96s | 10.09s | OK | 49.8 | 0.00 |  |
| hdr | 1080x1080p50_libx264_high_yuv420p_bt709_gop100_bit3650k_lcaac_160k_48k_2ch_en.mp4 | 1080x1080 | h264 | High@4.0 | 50.00 | 9.04s | 452 | OK | 13.44s | 9.53s | OK | 47.4 | 0.00 |  |
| hdr | 1080x1920p50_libx264_high_yuv420p_bt709_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1080x1920 | h264 | High@4.2 | 50.00 | 9.04s | 452 | OK | 20.07s | 15.87s | OK | 28.5 | 0.00 |  |
| hdr | 1280x720p25_libx264_high_yuv420p_bt709_gop50_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 13.55s | 9.07s | OK | 25.0 | 0.00 |  |
| hdr | 1280x720p25_libx264_high_yuv420p_bt709_gop50_bit5M_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 13.05s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.81s | 9.01s | OK | 50.2 | 0.00 |  |
| hdr | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit5M_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.89s | 8.99s | OK | 50.3 | 0.00 |  |
| hdr | 1920x1080p50_libx264_high_yuv420p_bt709_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | h264 | High@4.2 | 50.00 | 9.04s | 452 | OK | 20.42s | 16.44s | OK | 27.5 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-hlg10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 59.34s | 54.56s | OK | 8.3 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-pq10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 60.77s | 54.42s | OK | 8.3 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-sdr10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 64.79s | 58.40s | OK | 7.7 | 0.00 |  |
| hdr | 270x270p25_libx264_baseline_yuv420p_bt709_gop50_bit144k_lcaac_96k_48k_2ch_en.mp4 | 270x270 | h264 | Constrained Baseline@1.3 | 25.00 | 9.00s | 225 | OK | 14.00s | 8.93s | OK | 25.2 | 0.00 |  |
| hdr | 270x480p25_libx264_baseline_yuv420p_bt709_gop50_bit256k_lcaac_64k_48k_2ch_en.mp4 | 270x480 | h264 | Constrained Baseline@2.1 | 25.00 | 9.00s | 225 | OK | 12.61s | 8.93s | OK | 25.2 | 0.00 |  |
| hdr | 360x360p25_libx264_main_yuv420p_bt709_gop50_bit576k_lcaac_160k_48k_2ch_en.mp4 | 360x360 | h264 | Main@2.1 | 25.00 | 9.08s | 227 | OK | 12.79s | 9.11s | OK | 24.9 | 0.00 |  |
| hdr | 360x640p25_libx264_main_yuv420p_bt709_gop50_bit1024k_lcaac_160k_48k_2ch_en.mp4 | 360x640 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.11s | OK | 24.9 | 0.00 |  |
| hdr | 3840x2160p50_libx264_high_yuv420p_bt709_gop100_bit10M_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | h264 | High@5.2 | 50.00 | 9.04s | 452 | Fehler | 22.09s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: 2. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-hlg10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-pq10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-sdr10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 480x270p25_libx264_baseline_yuv420p_bt709_gop50_bit256k_lcaac_128k_48k_2ch_en.mp4 | 480x270 | h264 | Constrained Baseline@2.1 | 25.00 | 9.00s | 225 | OK | 15.13s | 8.94s | OK | 25.2 | 0.00 |  |
| hdr | 512x288p25_libx264_main_yuv420p_bt709_gop50_bit512k_lcaac_160k_48k_2ch_en.mp4 | 512x288 | h264 | Main@2.1 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 540x540p25_libx264_main_yuv420p_bt709_gop50_bit1150k_lcaac_160k_48k_2ch_en.mp4 | 540x540 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.88s | 9.05s | OK | 25.1 | 0.00 |  |
| hdr | 540x960p25_libx264_main_yuv420p_bt709_gop50_bit1800k_lcaac_160k_48k_2ch_en.mp4 | 540x960 | h264 | Main@3.1 | 25.00 | 9.08s | 227 | OK | 12.90s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 640x360p25_libx264_main_yuv420p_bt709_gop50_bit1024k_lcaac_160k_48k_2ch_en.mp4 | 640x360 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 720x1280p25_libx264_high_yuv420p_bt709_gop50_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 720x1280 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 12.94s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 720x1280p50_libx264_high_yuv420p_bt709_gop100_bit5M_lcaac_160k_48k_2ch_en.mp4 | 720x1280 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.94s | 9.01s | OK | 50.2 | 0.00 |  |
| hdr | 720x720p25_libx264_high_yuv420p_bt709_gop50_bit2250k_lcaac_160k_48k_2ch_en.mp4 | 720x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 12.92s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 960x540p25_libx264_main_yuv420p_bt709_gop50_bit2500k_lcaac_160k_48k_2ch_en.mp4 | 960x540 | h264 | Main@3.1 | 25.00 | 9.08s | 227 | OK | 12.98s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 960x540p50_libx264_main_yuv420p_bt709_gop100_bit2500k_lcaac_160k_48k_2ch_en.mp4 | 960x540 | h264 | Main@3.1 | 50.00 | 9.04s | 452 | OK | 12.72s | 8.99s | OK | 50.3 | 0.00 |  |

## Image Loading Performance Analysis

*   **Test Configuration (15.02.2026):**
    *   **Display Duration (`time_delay`):** 60.0 seconds
    *   **Fade Time (`fade_time`):** 20.0 seconds
    *   **Ken Burns Effect:** Enabled (`true`)
    *   **Hardware:** Raspberry Pi Zero 2

### Analysis of Loading Times and Transitions

The following table shows the timing behavior.
*   **Loading Time:** The time between the controller selecting the image ("Next item") and the start of the transition ("Transitioning"). During this time, the UI is blocked ("Freeze" of the previous image).
*   **Status:**
    *   🟢 **OK:** Loading time < 3 seconds (barely noticeable).
    *   🟡 **Medium:** Loading time 3–10 seconds (short freeze).
    *   🔴 **Long:** Loading time > 10 seconds (significant freeze of the previous image).

| Timestamp | File | Mode | Loading Time | Status | Ken Burns / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | | | | | |
| 14:00:23 | C01 (80kB) | Portrait | 0.6s | 🟢 | Scroll down, Zoom 8.00% |
| 14:01:24 | C02 (316kB) | Landscape | 0.9s | 🟢 | Zoom IN 22.02% |
| 14:02:25 | C03 (381kB) | Landscape | 1.0s | 🟢 | Zoom OUT 7.25% |
| 14:03:26 | C04 (128kB) | Landscape | 0.5s | 🟢 | Zoom IN 34.39% |
| 14:04:26 | C05 (105kB) | Landscape | 0.6s | 🟢 | Zoom OUT 7.37% |
| 14:05:27 | C06 (1MB) | Landscape | 0.6s | 🟢 | Zoom OUT 38.36% |
| 14:06:28 | C07 (690kB) | Landscape | 1.0s | 🟢 | Downsizing: 2048x1536 -> 2016x1512 |
| 14:07:30 | C08 (1MB) | Landscape | 2.2s | 🟢 | Downsizing: 3000x2000 -> 2268x1512 |
| 14:08:32 | C09 (3MB) | Landscape | **36.1s** | 🔴 | **Freeze!** Downsizing 12MP (4000x3000). CPU-Limit. |
| 14:10:11 | C10 (6MB) | Landscape | 1.7s | 🟢 | Downsizing 12MP. Surprisingly fast (Cache/Buffer?). |
| 14:11:13 | C11 (6MB) | Landscape | 2.8s | 🟢 | Downsizing 12MP. |
| 14:12:16 | C12 (7MB) | Landscape | **57.1s** | 🔴 | **Freeze!** Downsizing 16MP (5312x2988). Very high load. |
| 14:14:14 | C14 (9MB) | Landscape | **27.3s** | 🔴 | **Freeze!** Downsizing 24MP (6000x4000). |
| 14:15:43 | C15 (5MB) | Landscape | 6.7s | 🟡 | Downsizing 24MP. |
| 14:16:50 | C16 (15MB) | Landscape | 4.4s | 🟡 | Downsizing 24MP (Nikon Z6). |
| 14:17:55 | C17 (10MB) | Landscape | **20.2s** | 🔴 | **Freeze!** Downsizing 24MP. |
| 14:19:16 | C18 (8MB) | Landscape | **44.0s** | 🔴 | **Freeze!** Downsizing 16MP. |
| 14:21:03 | C19 (6MB) | Panorama | **43.6s** | 🔴 | **Freeze!** Downsizing Panorama (8192x1856). |
| 14:22:48 | C20 (7MB) | Landscape | **44.6s** | 🔴 | **Freeze!** Downsizing 16MP. |
| **Run 2** | | | | | |
| 14:24:33 | C01 (80kB) | Portrait | 0.5s | 🟢 | Scroll up, Zoom 8.00% |
| ... | (C02-C08) | ... | < 2s | 🟢 | Fast loading times as in Run 1. |
| 14:32:42 | C09 (3MB) | Landscape | **36.7s** | 🔴 | **Freeze!** Reproducibly slow (cf. 36.1s). |
| 14:34:21 | C10 (6MB) | Landscape | 1.7s | 🟢 | Fast again. |
| 14:36:25 | C12 (7MB) | Landscape | **51.5s** | 🔴 | **Freeze!** Reproducibly slow (cf. 57.1s). |
| 14:38:18 | C14 (9MB) | Landscape | **16.2s** | 🔴 | Faster than Run 1 (27s), but still long. |
| 14:39:44 | C15 (5MB) | Landscape | 4.4s | 🟡 | Acceptable for 24MP. |
| 14:40:49 | C16 (15MB) | Landscape | 8.2s | 🟡 | Slightly slower than Run 1 (4.4s). |
| 14:41:58 | C17 (10MB) | Landscape | 4.2s | 🟡 | Much faster than Run 1 (20.2s). |
| 14:43:03 | C18 (8MB) | Landscape | **41.9s** | 🔴 | **Freeze!** Reproducibly slow (cf. 44.0s). |

## Video Slideshow Performance Analysis (15.02.2026)

### Test Configuration
*   **Hardware:** Raspberry Pi Zero 2
*   **Video Mode:** `ffmpeg` (Frame Extraction)
*   **Settings:**
    *   `video_slideshow_time_delay`: 4.0s (Display duration per frame)
    *   `video_slideshow_fade_time`: 2.0s (Fade time)
    *   `video_slideshow_quality`: 3 (High quality)
    *   `video_slideshow_step_time`: 10s (Interval between frames in video)

### Metrics
*   **Start Delay:** Time from start command until the first frame is loaded (waiting for ffmpeg).
*   **Wait:** Time the viewer had to wait for the *next* frame.
    *   Target: **0.00s** (buffer is full).
    *   > 0.5s: ffmpeg can't keep up (stutter).
*   **Blend:** Actual duration of the fade.
    *   Target: **2.00s**.
    *   > 3.0s: System load is too high for smooth graphics.

### Results per Video

| Video File | Resolution | Bitrate (est.) | Start Delay | Avg Wait | Max Wait | Status | Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **E1** (FFMPEG) | 1280x720 | 8 Mbps | ~37s | 0.01s | 0.13s | 🟢 **Perfect** | Smooth playback. Buffer is always full. |
| **E2** (GOPRO) | 1280x960 | 16 Mbps | ~40s | 1.08s | **4.35s** | 🟡 **Marginal** | ffmpeg is slower than playback (4s). The viewer often has to wait 1-4 seconds for the next frame. |
| **E3** (SONY) | 1920x1080 | 25 Mbps | ~58s | **8.50s** | **16.38s** | 🔴 **Overloaded** | Unplayable. The Pi Zero 2 cannot decode and scale 1080p high-bitrate fast enough. Wait times are longer than the display time. |
| **E5** (FFMPEG) | 1280x720 | 3 Mbps | ~38s | 0.15s | 4.17s | 🟢 **Good** | Mostly smooth (239 frames). Occasional spikes (e.g., frame 16, 164) indicate brief IO or CPU bottlenecks. |
| **E7** (Super8) | 960x720 | 6 Mbps | ~17s | 0.45s | 3.54s | 🟡 **OK** | Acceptable, but ffmpeg is running at its limit. Occasional wait times of 1-3 seconds. |

### Timing Logic (Example with `time_delay: 60.0`, `fade_time: 20.0`)

*   **Loading (Downsizing):** Duration X (e.g., 30s). The previous image remains frozen on screen ("Freeze").
*   **Start (T=0):** The new image is ready. Logs are written.
*   **Phase 1 (T=0 to T=20):** Transition. The new image fades in. Ken Burns effect starts.
*   **Phase 2 (T=20 to T=60):** Image is fully visible. Ken Burns effect continues.
*   **End (T=60):** The 60 seconds are up. The controller wakes up and loads the next image.

### Test Files

*   C01-FotoScan_578x519_80kB.jpg
*   C02-CanonIXUS_1525x1025_316kB.jpg
*   C03-CanonIXUS_1535x1035_381kB.jpg
*   C04-FotoScan_956x578_128kB.jpg
*   C05-Resized_1600x900_105kB.jpg
*   C06-CanonPowershot_1600x1200_1MB.jpg
*   C07-DiMAGExi_2048x1536_690kB.jpg
*   C08-NiconCoolscan_3000x2000_1MB.jpg
*   C09-SamsungS22_4000x3000_3MB.jpg
*   C10-Pocophone_4032x3024_6MB.jpg
*   C11-Pocophone_4032x3024_6MB.jpg
*   C12-LGG5_5312x2988_7MB.jpg
*   C14-SonyNex7_6000x4000_9MB.jpg
*   C15-SonyNex7_6000x4000_5MB.jpg
*   C16-NikonZ6_6048x4024_15MB.jpg
*   C17-SonyNex7_6000x4000_10MB.jpg
*   C18-LGG5_5312x2988_8MB.jpg
*   C19-SonyNex7_8192x1856_6MB.jpg
*   C20-LGG5_5312x2988_7MB.jpg

### Analysis of Timings

*   **Small Images (e.g., C01-C07):**
    *   `Load` is between 0.06s and 0.64s.
    *   `Resize` is 0.00s, as the images do not exceed the 125% threshold and do not need to be reduced via `thumbnail()`.
    *   `Fade` is constant at ~20.04s.
    *   **Behavior:** Perfect.

*   **Large Images (e.g., C09, C10, C12, C18, C19, C20):**
    *   `Resize` takes between 25s and 40s here. This is the CPU-intensive `thumbnail()` operation.
    *   `Load` (Total load time) is correspondingly high (e.g., 38s, 43s, 58s, 68s).
    *   `Fade` is nevertheless constant at ~20.05s.
    *   **Behavior:** Perfect. The system freezes during loading as expected, but the transition afterwards is buttery smooth and precisely timed.

*   **Medium-sized Images (e.g., C08, C14, C15, C16, C17):**
    *   Something interesting can be seen here: `Resize` is 0.00s, although the images are large. This is because they do not exceed the 125% threshold.
    *   `Load` still takes a long time (25s - 32s). This is the time Pillow/pi3d needs to decode the large (but not *huge*) image file and upload it as a texture to the GPU.
    *   `Fade` is also constant here at ~20.00s.
    *   **Behavior:** Perfect. This shows that the optimization is effective and unnecessary `Downsizing` is avoided, yet the timing control still functions correctly.

### Summary

The timing control for the transitions now works exactly as desired. Load times are correctly decoupled from the animation time, resulting in buttery smooth and precisely timed cross-fades. The downsizing optimization also works as expected.