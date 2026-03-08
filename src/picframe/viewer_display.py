import time
import subprocess
import logging
import os
import sys
import random
from typing import Optional, List, Tuple
import threading
from datetime import datetime
from PIL import Image, ImageFilter, ImageFile
import numpy as np
import pi3d  # type: ignore
from picframe import mat_image, get_image_meta
from picframe.controller import VIDEO_EXTENSIONS
from picframe.video_extractor import VideoExtractor

import shlex
import shutil
import gc

# supported display modes for display switch
dpms_mode = ("unsupported", "pi", "x_dpms")


# utility functions with no dependency on ViewerDisplay properties
def txt_to_bit(txt):
    txt_map = {"title": 1, "caption": 2, "name": 4, "date": 8, "location": 16, "folder": 32}
    if txt in txt_map:
        return txt_map[txt]
    return 0


def parse_show_text(txt):
    show_text = 0
    txt = txt.lower()
    for txt_key in ("title", "caption", "name", "date", "location", "folder"):
        if txt_key in txt:
            show_text |= txt_to_bit(txt_key)
    return show_text


class ViewerDisplay:

    def __init__(self, config):
        self.__logger = logging.getLogger("viewer_display.ViewerDisplay")
        self.__blur_amount = config['blur_amount']
        self.__blur_zoom = config['blur_zoom']
        self.__blur_edges = config['blur_edges']
        self.__edge_alpha = config['edge_alpha']

        self.__mat_images, self.__mat_images_tol = self.__get_mat_image_control_values(config['mat_images'])
        # If starting after a video (exit code 10), force a black background to avoid a color flash.
        # Check environment variable from watcher.sh
        if os.getenv('PICFRAME_RESTART_CODE') == '10':
            self.__solid_background = [0.2, 0.2, 0.3, 1.0] # Force dark blue background on video restart
        else:
            self.__solid_background = config['solid_background']
        self.__outer_mat_color = config['outer_mat_color']
        self.__inner_mat_color = config['inner_mat_color']
        self.__outer_mat_border = config['outer_mat_border']
        self.__inner_mat_border = config['inner_mat_border']
        self.__outer_mat_use_texture = config['outer_mat_use_texture']
        self.__inner_mat_use_texture = config['inner_mat_use_texture']
        self.__mat_resource_folder = os.path.expanduser(config['mat_resource_folder'])

        self.__fps = config['fps']
        self.__background = config['background']
        self.__mat_type = config['mat_type']
        self.__blend_type = {"blend": 0.0, "burn": 1.0, "bump": 2.0}[config['blend_type']]
        self.__font_file = os.path.expanduser(config['font_file'])
        self.__shader = os.path.expanduser(config['shader'])
        self.__show_text_tm = float(config['show_text_tm'])
        self.__show_text_fm = config['show_text_fm']
        self.__show_text_sz = config['show_text_sz']
        self.__show_text = parse_show_text(config['show_text'])
        self.__text_justify = config['text_justify'].upper()
        self.__text_wdt_offset_pct = config.get('text_wdt_offset_pct', 3.0)
        self.__text_hgt_offset_pct = config.get('text_hgt_offset_pct', 1.5) # Default 1.5%
        self.__text_bkg_hgt = config['text_bkg_hgt'] if 0 <= config['text_bkg_hgt'] <= 1 else 0.25
        self.__text_opacity = config['text_opacity']
        self.__fit = config['fit']
        self.__video_fit_display = config['video_fit_display']
        self.__geo_suppress_list = config['geo_suppress_list']
        self.__kenburns = config['kenburns']
        
        # New Aspect Ratio Logic
        self.__screen_ar = self.__parse_aspect_ratio(config.get('screen_aspect_ratio', '16:9')) or (16/9)
        self.__viewport_ar = self.__parse_aspect_ratio(config.get('viewport_aspect_ratio', '16:9')) or self.__screen_ar
        self.__landscape_crop_ar = self.__parse_aspect_ratio(config.get('landscape_crop_to_aspect_ratio'))
        self.__portrait_crop_ar = self.__parse_aspect_ratio(config.get('portrait_crop_to_aspect_ratio'))
        
        # Sanity check crop ARs
        if self.__landscape_crop_ar and (self.__landscape_crop_ar > 5.0 or self.__landscape_crop_ar < 0.2):
             self.__logger.warning(f"Sanity Check: Configured landscape_crop_to_aspect_ratio {self.__landscape_crop_ar} is unreasonable. Ignoring.")
             self.__landscape_crop_ar = None
             
        if self.__portrait_crop_ar and (self.__portrait_crop_ar > 5.0 or self.__portrait_crop_ar < 0.2):
             self.__logger.warning(f"Sanity Check: Configured portrait_crop_to_aspect_ratio {self.__portrait_crop_ar} is unreasonable. Ignoring.")
             self.__portrait_crop_ar = None

        if self.__kenburns:
            self.__kb_landscape_zoom_direction = config.get('kenburns_landscape_zoom_direction', 'random')
            self.__kb_portrait_scroll_direction = config.get('kenburns_portrait_scroll_direction', 'random')
            
            # Helper to normalize percentage values (handle 0.xx as xx%)
            def get_pct(key, default):
                val = abs(config.get(key, default))
                if val < 1.0: return val * 100.0
                return val

            self.__kb_portrait_border_pct = get_pct('kenburns_portrait_border_pct', 5.0)
            self.__kb_landscape_zoom_pct = get_pct('kenburns_landscape_zoom_pct', 10.0)
            self.__kb_landscape_wobble_pct = get_pct('kenburns_landscape_wobble_pct', 5.0)
            self.__kb_portrait_wobble_pct = get_pct('kenburns_portrait_wobble_pct', 5.0)
            self.__kb_panorama_zoom_pct = get_pct('kenburns_panorama_zoom_pct', 10.0)

            self.__kb_random_pan = config.get('kenburns_random_pan', True)
            self.__kb_panorama_zoom_direction = config.get('kenburns_panorama_zoom_direction', 'random')
            self.__kb_panorama_scroll_direction = config.get('kenburns_panorama_scroll_direction', 'random')
            self.__panorama_crop_ar = self.__parse_aspect_ratio(config.get('panorama_crop_to_aspect_ratio'))
            self.__kb_current_state = {}
            self.__kb_previous_state = {}
            self.__fit = False
            self.__blur_edges = False

        if self.__blur_zoom < 1.0:
            self.__blur_zoom = 1.0
        self.__display_x = int(config['display_x'])
        self.__display_y = int(config['display_y'])
        self.__display_w = None if config['display_w'] is None else int(config['display_w'])
        self.__display_h = None if config['display_h'] is None else int(config['display_h'])
        self.__display_power = int(config['display_power'])
        self.__use_sdl2 = config['use_sdl2']
        self.__use_glx = config['use_glx']
        self.__alpha = 0.0  # alpha - proportion front image to back
        self.__delta_alpha = 1.0
        self.__transition_start_tm = 0.0
        self.__display = None
        self.__slide = None
        self.__slide_bg = None # Second sprite for background image (Ken Burns)
        self.__background_sprite = None
        self.__flat_shader = None
        self.__textblocks = [None, None]
        self.__text_bkg = None
        self.__sfg = None  # slide for background
        self.__sbg = None  # slide for foreground
        self.__last_frame_tex = None  # slide for last frame of video
        self.__skip_draw = False # Flag to skip the next draw call
        self.__video_path = None  # path to video file
        self.__next_tm = 0.0
        self.__name_tm = 0.0
        self.__in_transition = False
        self.__matter = None
        self.__prev_clock_time = None
        self.__clock_overlay = None
        self.__show_clock = config['show_clock']
        self.__clock_justify = config['clock_justify']
        self.__clock_text_sz = config['clock_text_sz']
        self.__clock_format = config['clock_format']
        self.__clock_opacity = config['clock_opacity']
        self.__clock_top_bottom = config['clock_top_bottom']
        self.__clock_wdt_offset_pct = config['clock_wdt_offset_pct']
        self.__clock_hgt_offset_pct = config['clock_hgt_offset_pct']
        self.__image_overlay = None
        self.__prev_overlay_time = None
        self.__kmsblank_proc = None
        ImageFile.LOAD_TRUNCATED_IMAGES = True  # occasional damaged file hangs app
        
        # Icons
        self.__icon_path = config.get('icon_path')
        if self.__icon_path:
             self.__icon_path = os.path.expanduser(self.__icon_path)
        self.__icon_wdt_offset_pct = config.get('icon_wdt_offset_pct', 2.0)
        self.__icon_hgt_offset_pct = config.get('icon_hgt_offset_pct', 2.0)
        self.__icon_opacity = config.get('icon_opacity', 1.0)
        self.__icon_play = None
        self.__icon_pause = None
        self.__icon_skipf = None
        self.__icon_download = None
        self.__icon_offline = None
        self.__icon_sync = None
        self.__icon_nowlan = None
        self.__icon_eject = None
        self.__system_state = None
        self.__icon_sprite = None
        self.__video_slideshow_playing = False

        # Framebuffer settings for black screen
        self.__fb_width = 1920 # TODO: read from config or detect
        self.__fb_height = 1080
        self.__fb_bpp = 32 # bits_per_pixel for RGBA (4 bytes * 8 bits)
        self.__fb_bytes = int(self.__fb_width * self.__fb_height * (self.__fb_bpp / 8))
        self.__logger.info(f"Picframe FPS: {self.__fps}")
        
        # Threading for async image loading
        self.__loading_thread = None
        self.__loading_result = None
        self.__next_pics = None
        self.__paused = False
        self.__last_load_time = 0.0
        self.__last_resize_time = 0.0
        self.__was_in_transition = False
        
    def __parse_aspect_ratio(self, ar_str):
        if not ar_str:
            return None
        try:
            s = str(ar_str)
            if ':' not in s:
                return float(s)
            
            w, h = map(float, s.split(':'))
            return w / h if h != 0 else 1.0
        except Exception:
            return None

    def __get_viewport_size(self):
        if self.__display is None:
             return 0, 0
        
        if self.__viewport_ar < self.__screen_ar:
             # Pillarbox (fit height)
             vp_h = self.__display.height
             vp_w = vp_h * self.__viewport_ar
        else:
             # Letterbox (fit width) or Match
             vp_w = self.__display.width
             vp_h = vp_w / self.__viewport_ar

        if vp_w > 10000 or vp_h > 10000:
             self.__logger.warning(f"DEBUG: Huge viewport calculated! vp={vp_w}x{vp_h}. Display={self.__display.width}x{self.__display.height}. AR_VP={self.__viewport_ar}, AR_Screen={self.__screen_ar}")

        return vp_w, vp_h

    def _show_black_screen(self):
        self.__logger.info("--- Showing Black Screen via dd ---")
        command = ["dd", "if=/dev/zero", f"of=/dev/fb0", f"bs={self.__fb_bytes}", "count=1"]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except Exception as e:
            self.__logger.warning(f"Could not blank screen with dd: {e}")

    def _play_video_subprocess(self, video_path):
        self.__logger.info("--- Starting Video Playback via Subprocess ---")
        command = ["mpv", "--fullscreen", "--no-osc", video_path]
        try:
            subprocess.run(command, check=True, timeout=3600) # Long timeout for videos
        except Exception as e:
            self.__logger.error(f"An error occurred during video playback: {e}")


    @property
    def display_is_on(self):
        if self.__display_power == 0:
            try:  # vcgencmd only applies to raspberry pi
                state = str(subprocess.check_output(["vcgencmd", "display_power"]))
                if (state.find("display_power=1") != -1):
                    return True
                else:
                    return False
            except (FileNotFoundError, ValueError, OSError) as e:
                self.__logger.debug("Display ON/OFF is vcgencmd, but an error occurred")
                self.__logger.debug("Cause: %s", e)
            return True
        elif self.__display_power == 1:
            try:  # try xset on linux, DPMS has to be enabled
                output = subprocess.check_output(["xset", "-display", ":0", "-q"])
                if output.find(b'Monitor is On') != -1:
                    return True
                else:
                    return False
            except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
                self.__logger.debug("Display ON/OFF is X with dpms enabled, but an error occurred")
                self.__logger.debug("Cause: %s", e)
            return True
        elif self.__display_power == 2:
            try:
                output = subprocess.check_output(["wlr-randr"])
                if output.find(b'Enabled: yes') != -1:
                    return True
                else:
                    return False
            except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
                self.__logger.debug("Display ON/OFF is wlr-randr, but an error occurred")
                self.__logger.debug("Cause: %s", e)
            return True
        else:
            self.__logger.warning("Unsupported setting for display_power=%d.", self.__display_power)
            return True

    @display_is_on.setter
    def display_is_on(self, on_off):
        self.__logger.debug("Switch display (display_power=%d).", self.__display_power)
        if self.__display_power == 0:
            try:  # vcgencmd only applies to raspberry pi
                if on_off is True:
                    subprocess.call(["vcgencmd", "display_power", "1"])
                else:
                    subprocess.call(["vcgencmd", "display_power", "0"])
            except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError) as e:
                self.__logger.debug("Display ON/OFF is vcgencmd, but an error occured")
                self.__logger.debug("Cause: %s", e)
        elif self.__display_power == 1:
            try:  # try xset on linux, DPMS has to be enabled
                if on_off is True:
                    subprocess.call(["xset", "-display", ":0", "dpms", "force", "on"])
                else:
                    subprocess.call(["xset", "-display", ":0", "dpms", "force", "off"])
            except (ValueError, TypeError) as e:
                self.__logger.debug("Display ON/OFF is xset via dpms, but an error occured")
                self.__logger.debug("Cause: %s", e)
        elif self.__display_power == 2:
            try:  # try wlr-randr for RPi5 with wayland desktop
                wlr_randr_cmd = ["wlr-randr", "--output", "HDMI-A-1"]
                wlr_randr_cmd.append('--on' if on_off else '--off')
                subprocess.call(wlr_randr_cmd)
            except (ValueError, TypeError) as e:
                self.__logger.debug("Display ON/OFF is wlr-randr, but an error occured")
                self.__logger.debug("Cause: %s", e)
        else:
            self.__logger.warning("Unsupported setting for display_power=%d.", self.__display_power)

    def set_show_text(self, txt_key=None, val="ON"):
        if txt_key is None:
            self.__show_text = 0  # no arguments signals turning all off
        else:
            bit = txt_to_bit(txt_key)  # convert field name to relevant bit 1,2,4,8,16 etc
            if val == "ON":
                self.__show_text |= bit  # turn it on
            else:  # TODO anything else ok to turn it off?
                bits = 65535 ^ bit
                self.__show_text &= bits  # turn it off

    def text_is_on(self, txt_key):
        return self.__show_text & txt_to_bit(txt_key)

    def reset_name_tm(self, pic=None, paused=None, side=0, pair=False):
        # only extend i.e. if after initial fade in
        if pic is not None and paused is not None:  # text needs to be refreshed
            self.__make_text(pic, paused, side, pair)
        self.__name_tm = max(self.__name_tm, time.time() + self.__show_text_tm)

    def set_brightness(self, val):
        self.__slide.unif[55] = val  # take immediate effect
        if self.__clock_overlay:  # will be set to None if not text
            self.__clock_overlay.sprite.set_alpha(val)
        if self.__image_overlay:
            self.__image_overlay.set_alpha(val)
        for txt in self.__textblocks:  # must be list
            if txt:
                txt.sprite.set_alpha(val)

    def get_brightness(self):
        return round(self.__slide.unif[55], 2)

    def set_matting_images(self, val):
        try:
            float_val = float(val)
            if round(float_val, 4) == 0.0:
                val = "true"
            if round(float_val, 4) == 1.0:
                val = "false"
        except Exception:
            pass
        self.__mat_images, self.__mat_images_tol = self.__get_mat_image_control_values(val)

    def get_matting_images(self):
        if self.__mat_images and self.__mat_images_tol > 0:
            return self.__mat_images_tol
        elif self.__mat_images and self.__mat_images_tol == -1:
            return 0
        else:
            return 1

    @property
    def clock_is_on(self):
        return self.__show_clock

    @clock_is_on.setter
    def clock_is_on(self, val):
        self.__show_clock = val

    def __create_image_pair(self, im1, im2):
        sep = 8
        if im1.width > im2.width:
            im1 = im1.resize((im2.width, int(im1.height * im2.width / im1.width)), resample=Image.BICUBIC)
        else:
            im2 = im2.resize((im1.width, int(im2.height * im1.width / im2.width)), resample=Image.BICUBIC)
        dst = Image.new('RGB', (im1.width + im2.width + sep, min(im1.height, im2.height)))
        dst.paste(im1, (0, 0))
        dst.paste(im2, (im1.width + sep, 0))
        return dst

    def __orientate_image(self, im, pic):
        ext = os.path.splitext(pic.fname)[1].lower()
        if ext in ('.heif', '.heic'):
            return im
        orientation = pic.orientation
        if orientation == 2:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            im = im.transpose(Image.ROTATE_180)
        elif orientation == 4:
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
        elif orientation == 6:
            im = im.transpose(Image.ROTATE_270)
        elif orientation == 7:
            im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
        elif orientation == 8:
            im = im.transpose(Image.ROTATE_90)
        return im

    def __get_mat_image_control_values(self, mat_images_value):
        on = True
        val = 0.01
        org_val = str(mat_images_value).lower()
        if org_val in ('true', 'yes', 'on'):
            val = -1
        elif org_val in ('false', 'no', 'off'):
            on = False
        else:
            try:
                val = float(org_val)
            except Exception:
                self.__logger.warning("Invalid value for config option 'mat_images'. Using default.")
        return (on, val)

    def __get_aspect_diff(self, screen_size, image_size):
        screen_aspect = screen_size[0] / screen_size[1]
        image_aspect = image_size[0] / image_size[1]
        if screen_aspect > image_aspect:
            diff_aspect = 1 - (image_aspect / screen_aspect)
        else:
            diff_aspect = 1 - (screen_aspect / image_aspect)
        return (screen_aspect, image_aspect, diff_aspect)

    def __prepare_image(self, pics, size=None):
        """
        Loads and prepares the PIL Image in a background thread (CPU bound).
        Does NOT create the pi3d.Texture (GPU bound, must be main thread).
        """
        try:
            self.__logger.debug(f"loading images: {pics[0].fname} {pics[1].fname if pics[1] else ''}")
            if self.__mat_images and self.__matter is None:
                self.__matter = mat_image.MatImage(
                    display_size=(self.__display.width, self.__display.height),
                    resource_folder=self.__mat_resource_folder,
                    mat_type=self.__mat_type,
                    outer_mat_color=self.__outer_mat_color,
                    inner_mat_color=self.__inner_mat_color,
                    outer_mat_border=self.__outer_mat_border,
                    inner_mat_border=self.__inner_mat_border,
                    outer_mat_use_texture=self.__outer_mat_use_texture,
                    inner_mat_use_texture=self.__inner_mat_use_texture)

            if pics[0]:
                im = get_image_meta.GetImageMeta.get_image_object(pics[0].fname)
                if im is None:
                    self.__logger.warning("Failed to load image object for %s", pics[0].fname)
                    return None
                self.__logger.debug("Image loaded: %s, size: %s, mode: %s", pics[0].fname, im.size, im.mode)

                # --- Start of new optimized loading block ---

                # A. Get original dimensions and check if orientation requires swapping them for aspect calculation
                original_w, original_h = im.size
                is_rotated = pics[0].orientation in [5, 6, 7, 8]
                oriented_w = original_h if is_rotated else original_w
                oriented_h = original_w if is_rotated else original_h
                
                # B. Calculate target dimensions based on Viewport and Ken Burns settings
                vp_w, vp_h = self.__get_viewport_size()
                if vp_w == 0 and size: vp_w, vp_h = size # Fallback
                
                req_w, req_h = 0, 0
                if vp_w > 0 and vp_h > 0:
                    image_ar = oriented_w / oriented_h
                    viewport_ar = vp_w / vp_h
                    
                    if self.__kenburns:
                        if viewport_ar > image_ar: # Portrait-like
                            zoom = 1.0 + (self.__kb_portrait_wobble_pct / 100.0)
                            req_w = vp_w * zoom
                            req_h = req_w / image_ar
                        elif image_ar > self.__screen_ar: # Panorama-like
                            zoom = 1.0 + (self.__kb_panorama_zoom_pct / 100.0)
                            req_h = vp_h * zoom
                            req_w = req_h * image_ar
                        else: # Landscape-like
                            zoom = 1.0 + (self.__kb_landscape_zoom_pct / 100.0)
                            req_h = vp_h * zoom
                            req_w = req_h * image_ar
                    else: # No Ken Burns
                        if viewport_ar > image_ar:
                            req_w = vp_w
                            req_h = req_w / image_ar
                        else:
                            req_h = vp_h
                            req_w = req_h * image_ar
                
                max_w = int(req_w)
                max_h = int(req_h)

                # C. Use draft mode for huge performance gain on JPEGs
                # The draft size must be based on the original (non-oriented) dimensions.
                draft_w, draft_h = (max_h, max_w) if is_rotated else (max_w, max_h)
                try:
                    im.draft(None, (draft_w, draft_h))
                    self.__logger.debug(f"Drafting image to fit ~{draft_w}x{draft_h}")
                except Exception: # draft is only for JPEG, might fail on others
                    pass

                # D. Apply orientation transpose. This is a lazy operation.
                if pics[0].orientation != 1:
                    im = self.__orientate_image(im, pics[0])
                    self.__logger.debug("Image after lazy orientation: size: %s, mode: %s", im.size, im.mode)

                # E. Final resize. This triggers the actual (drafted) load and resize.
                current_w, current_h = im.size
                resize_start = time.time()
                if current_w > max_w * 1.25 or current_h > max_h * 1.25:
                    im.thumbnail((max_w, max_h), Image.Resampling.BILINEAR)
                    self.__last_resize_time = time.time() - resize_start
                    self.__logger.info(f"Downsized from {current_w}x{current_h} to {max_w}x{max_h} in {self.__last_resize_time:.2f}s")
                else:
                    self.__logger.debug(f"Skipping resize (within 125%): {im.size} vs target {max_w}x{max_h}")
                    self.__last_resize_time = 0.0
                # --- End of new optimized loading block ---
 
            # Determine cropping logic based on orientation and Ken Burns state
            image_ar = im.width / im.height
            is_portrait = image_ar < self.__viewport_ar
            is_panorama = image_ar > self.__screen_ar
            target_crop_ar = None

            if self.__kenburns:
                # If Ken Burns is ON:
                # Do NOT crop physically. We handle the "crop" (scroll limits) in __calculate_kenburns_transform.
                # This ensures we have the full image resolution available and avoids destructive cropping.
                # EXCEPTION: Panorama with configured crop to save resources.
                if is_panorama and self.__panorama_crop_ar:
                    target_crop_ar = self.__panorama_crop_ar
                else:
                    target_crop_ar = None
            else:
                # If Ken Burns is OFF:
                # - Apply cropping if configured for the respective orientation
                if is_portrait and self.__portrait_crop_ar:
                    target_crop_ar = self.__portrait_crop_ar
                elif not is_portrait and self.__landscape_crop_ar:
                    target_crop_ar = self.__landscape_crop_ar

            if target_crop_ar:
                image_ar = im.width / im.height
                if (image_ar / target_crop_ar) > 1.01:
                    # Image is wider than target: Crop Width
                    new_width = target_crop_ar * im.height
                    left = (im.width - new_width) / 2
                    im = im.crop((left, 0, left + new_width, im.height))
                elif (target_crop_ar / image_ar) > 1.01:
                    # Image is taller than target: Crop Height
                    new_height = im.width / target_crop_ar
                    top = (im.height - new_height) / 2
                    im = im.crop((0, top, im.width, top + new_height))
                self.__logger.debug("Image after cropping: size: %s, mode: %s", im.size, im.mode)

            if pics[1]:
                im2 = get_image_meta.GetImageMeta.get_image_object(pics[1].fname)
                if im2 is None:
                    self.__logger.warning("Failed to load image object for %s", pics[1].fname)
                    return None
                self.__logger.debug("Second image loaded: %s, size: %s, mode: %s", pics[1].fname, im2.size, im2.mode)
                if pics[1].orientation != 1:
                    im2 = self.__orientate_image(im2, pics[1])
                    self.__logger.debug("Second image after orientation: size: %s, mode: %s", im2.size, im2.mode)

            screen_aspect, image_aspect, diff_aspect = self.__get_aspect_diff(size, im.size)

            if self.__mat_images and diff_aspect > self.__mat_images_tol:
                self.__logger.debug("Applying matting to image(s).")
                if not pics[1]:
                    im = self.__matter.mat_image((im,))
                else:
                    im = self.__matter.mat_image((im, im2))
                self.__logger.debug("Image after matting: size: %s, mode: %s", im.size, im.mode)
            else:
                if pics[1]:
                    self.__logger.debug("Creating image pair without matting.")
                    im = self.__create_image_pair(im, im2)
                    self.__logger.debug("Image after pairing: size: %s, mode: %s", im.size, im.mode)

            (w, h) = im.size
            screen_aspect, image_aspect, diff_aspect = self.__get_aspect_diff(size, im.size)

            if self.__blur_edges and size:
                if diff_aspect > 0.01:
                    (sc_b, sc_f) = (size[1] / im.size[1], size[0] / im.size[0])
                    if screen_aspect > image_aspect:
                        (sc_b, sc_f) = (sc_f, sc_b)
                    (w, h) = (round(size[0] / sc_b / self.__blur_zoom), round(size[1] / sc_b / self.__blur_zoom))
                    (x, y) = (round(0.5 * (im.size[0] - w)), round(0.5 * (im.size[1] - h)))
                    box = (x, y, x + w, y + h)
                    blr_sz = [int(x * 512 / size[0]) for x in size]
                    im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
                    im_b = im_b.filter(ImageFilter.GaussianBlur(self.__blur_amount))
                    im_b = im_b.resize(size, resample=Image.BICUBIC)
                    im_b.putalpha(round(255 * self.__edge_alpha))
                    im = im.resize([int(x * sc_f) for x in im.size], resample=Image.BICUBIC)
                    im_b.paste(im, box=(round(0.5 * (im_b.size[0] - im.size[0])), 
                                        round(0.5 * (im_b.size[1] - im.size[1]))))
                    im = im_b
                self.__logger.debug("Image after blurring: size: %s, mode: %s", im.size, im.mode)
            return im
        except Exception as e:
            self.__logger.warning("Can't prepare image from file: \"%s\" or \"%s\"", pics[0].fname, pics[1])
            self.__logger.warning("Cause: %s", e)
            return None

    def __async_load_wrapper(self, pics, size):
        """Wrapper to run __prepare_image in a thread and store result."""
        self.__loading_result = self.__prepare_image(pics, size)

    def __tex_load_sync(self, pics, size=None):
        """Synchronous wrapper for single image display."""
        start_tm = time.time()
        im = self.__prepare_image(pics, size)
        if im is None:
            return None
        try:
            tex = pi3d.Texture(im, blend=True, m_repeat=False, free_after_load=True)
            tex.load_opengl()  # Force upload to GPU to prevent stutter during transition
            self.__last_load_time = time.time() - start_tm
            return tex
        except Exception as e:
            self.__logger.warning("Can't create tex from image: %s", e)
            return None

    def __make_text(self, pic, paused, side=0, pair=False):
        info_strings = []
        if pic is not None and (self.__show_text > 0 or paused):
            if (self.__show_text & 1) == 1 and pic.title is not None:
                info_strings.append(pic.title)
            if (self.__show_text & 2) == 2 and pic.caption is not None:
                info_strings.append(pic.caption)
            if (self.__show_text & 4) == 4:
                info_strings.append(os.path.basename(pic.fname))
            if (self.__show_text & 8) == 8 and pic.exif_datetime > 0:
                fdt = time.strftime(self.__show_text_fm, time.localtime(pic.exif_datetime))
                info_strings.append(fdt)
            if (self.__show_text & 16) == 16 and pic.location is not None:
                location = pic.location
                if self.__geo_suppress_list is not None:
                    for part in self.__geo_suppress_list:
                        location = location.replace(part, "")
                    location = location.replace(" ,", "")
                    location = location.strip(", ")
                info_strings.append(location)
            if (self.__show_text & 32) == 32:
                info_strings.append(os.path.basename(os.path.dirname(pic.fname)))
            if paused:
                info_strings.append("PAUSED")
        final_string = " • ".join(info_strings)
        self.__logger.debug("__make_text: final_string = '%s'", final_string)

        block = None
        if len(final_string) > 0:
            wdt_offset = int(self.__display.width * self.__text_wdt_offset_pct / 100)
            if side == 0 and not pair:
                c_rng = self.__display.width - (wdt_offset * 2)
            else:
                c_rng = self.__display.width * 0.5 - wdt_offset
            opacity = int(255 * float(self.__text_opacity) * self.get_brightness())
            block = pi3d.FixedString(self.__font_file, final_string, shadow_radius=3, font_size=self.__show_text_sz,
                                     shader=self.__flat_shader, justify=self.__text_justify, width=c_rng,
                                     color=(255, 255, 255, opacity))
            # Force texture upload to GPU
            if block.sprite.buf and block.sprite.buf[0].textures:
                 block.sprite.buf[0].textures[0].load_opengl()
            self.__logger.debug("__make_text: FixedString created. Sprite size: %s, alpha: %s", (block.sprite.width, block.sprite.height), block.sprite.alpha())
            adj_x = (c_rng - block.sprite.width) // 2
            if self.__text_justify == "L":
                adj_x *= -1
            elif self.__text_justify == "C":
                adj_x = 0
            if side == 0 and not pair:
                x = adj_x
            else:
                x = adj_x + int(self.__display.width * 0.25 * (-1.0 if side == 0 else 1.0))
            hgt_offset = int(self.__display.height * self.__text_hgt_offset_pct / 100)
            y = (block.sprite.height - self.__display.height) // 2 + hgt_offset
            block.sprite.position(x, y, 0.1)
            block.sprite.set_alpha(0.0)
        if side == 0:
            self.__textblocks[1] = None
        self.__textblocks[side] = block

    def __draw_clock(self):
        current_time = datetime.now().strftime(self.__clock_format)
        if self.__clock_overlay is None or current_time != self.__prev_clock_time:
            wdt_offset = int(self.__display.width * self.__clock_wdt_offset_pct / 100)
            hgt_offset = int(self.__display.height * self.__clock_hgt_offset_pct / 100)
            width = self.__display.width - (wdt_offset * 2)
            
            clock_text = current_time
            
            if os.path.isfile("/dev/shm/clock.txt"):
                with open("/dev/shm/clock.txt", "r") as f:
                    extra_text = f.read()
                    clock_text = f"{clock_text}\n{extra_text}"
            opacity = int(255 * float(self.__clock_opacity))
            self.__clock_overlay = pi3d.FixedString(self.__font_file, clock_text, font_size=self.__clock_text_sz,
                                                    shader=self.__flat_shader, width=width, shadow_radius=3,
                                                    justify=self.__clock_justify, color=(255, 255, 255, opacity))
            # Force texture upload to GPU
            if self.__clock_overlay.sprite.buf and self.__clock_overlay.sprite.buf[0].textures:
                 self.__clock_overlay.sprite.buf[0].textures[0].load_opengl()
            self.__logger.debug("__draw_clock: FixedString created. Sprite size: %s, alpha: %s", (self.__clock_overlay.sprite.width, self.__clock_overlay.sprite.height), self.__clock_overlay.sprite.alpha())
            self.__clock_overlay.sprite.set_alpha(self.get_brightness())
            x = (width - self.__clock_overlay.sprite.width) // 2
            if self.__clock_justify == "L":
                x *= -1
            elif self.__clock_justify == "C":
                x = 0
            y = (self.__display.height - self.__clock_overlay.sprite.height) // 2 - hgt_offset
            if self.__clock_top_bottom == "B":
                y *= -1
            self.__clock_overlay.sprite.position(x, y, 0.1)
            self.__prev_clock_time = current_time

        if self.__clock_overlay:
            self.__clock_overlay.sprite.draw()
            
    def __draw_icon(self):
        if self.__icon_sprite:
            tex = None
            # Priority list for icons
            if self.__system_state == "eject" and self.__icon_eject:
                tex = self.__icon_eject
            elif self.__system_state == "offline" and self.__icon_offline:
                tex = self.__icon_offline
            elif self.__system_state == "nowlan" and self.__icon_nowlan:
                tex = self.__icon_nowlan
            elif self.__system_state == "download" and self.__icon_download:
                tex = self.__icon_download
            elif self.__system_state == "sync" and self.__icon_sync:
                tex = self.__icon_sync
            elif self.__video_slideshow_playing and self.__icon_skipf:
                tex = self.__icon_skipf
            elif self.__paused:
                tex = self.__icon_pause
            else:
                tex = self.__icon_play
            
            if tex:
                self.__icon_sprite.set_draw_details(self.__flat_shader, [tex])
                self.__icon_sprite.set_alpha(self.get_brightness() * float(self.__icon_opacity))
                # Set scale to native texture dimensions using .scale() to trigger matrix update
                self.__icon_sprite.scale(float(tex.ix), float(tex.iy), 1.0)
                
                vp_w, vp_h = self.__get_viewport_size()
                
                padding_x = vp_w * self.__icon_wdt_offset_pct / 100.0
                padding_y = vp_h * self.__icon_hgt_offset_pct / 100.0
                # Position bottom right of viewport
                # pi3d coordinates are centered (0,0). Right edge is +width/2, Bottom edge is -height/2.
                x = (vp_w / 2.0) - padding_x - (tex.ix / 2.0)
                y = -(vp_h / 2.0) + padding_y + (tex.iy / 2.0)
                
                self.__icon_sprite.position(x, y, 0.1)
                self.__icon_sprite.draw()

    def __draw_overlay(self):
        overlay_file = "/dev/shm/overlay.png"
        if not os.path.isfile(overlay_file):
            self.__image_overlay = None
            return
        change_time = os.path.getmtime(overlay_file)
        if self.__prev_overlay_time is None or self.__prev_overlay_time < change_time:
            self.__prev_overlay_time = change_time
            overlay_texture = pi3d.Texture(overlay_file,
                                           blend=False,
                                           free_after_load=True,
                                           mipmap=False)
            overlay_texture.load_opengl() # Force upload
            self.__image_overlay = pi3d.Sprite(w=self.__display.width,
                                               h=self.__display.height,
                                               z=4.1)
            self.__image_overlay.set_draw_details(self.__flat_shader, [overlay_texture])
            self.__image_overlay.set_alpha(self.get_brightness())
        if self.__image_overlay is not None:
            self.__image_overlay.draw()

    @property
    def display_width(self):
        return self.__display.width

    @property
    def display_height(self):
        return self.__display.height

    def is_in_transition(self):
        return self.__in_transition

    def slideshow_start(self):
        self.__display = pi3d.Display.create(
            x=self.__display_x, y=self.__display_y,
            w=self.__display_w, h=self.__display_h, frames_per_second=self.__fps,
            display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR | pi3d.DISPLAY_CONFIG_NO_FRAME,
            background=self.__solid_background, use_glx=self.__use_glx,
            use_sdl2=self.__use_sdl2)
        
        # Sanity check and correct aspect ratios based on actual display dimensions
        if self.__display:
            actual_ar = self.__display.width / self.__display.height
            # If configured screen AR is unreasonable or differs significantly from actual, use actual.
            if self.__screen_ar is None or self.__screen_ar > 10.0 or self.__screen_ar < 0.1 or abs(self.__screen_ar - actual_ar) > 0.1:
                 self.__logger.warning(f"Sanity Check: Configured screen_aspect_ratio {self.__screen_ar} seems wrong for display {self.__display.width}x{self.__display.height}. Using actual AR {actual_ar:.3f}.")
                 self.__screen_ar = actual_ar
            
            # If viewport AR is unreasonable, reset to screen AR
            if self.__viewport_ar is None or self.__viewport_ar > 10.0 or self.__viewport_ar < 0.1:
                 self.__logger.warning(f"Sanity Check: Configured viewport_aspect_ratio {self.__viewport_ar} is unreasonable. Resetting to screen AR {self.__screen_ar:.3f}.")
                 self.__viewport_ar = self.__screen_ar

        self.__logger.debug(f"DEBUG: Display initialized: {self.__display.width}x{self.__display.height}")
        self.__logger.debug(f"DEBUG: Final AR - Screen: {self.__screen_ar:.3f}, Viewport: {self.__viewport_ar:.3f}")

        camera = pi3d.Camera(is_3d=False)
        shader = pi3d.Shader(self.__shader)
        self.__blend_shader = shader # Keep reference to blend shader for video slideshows
        
        # Create a unit sprite (1x1). We will scale it dynamically for each image
        # to achieve "Aspect Fill" via geometry instead of shader math.
        self.__slide = pi3d.Sprite(camera=camera, w=1.0, h=1.0, z=5.0)
        
        self.__slide.set_shader(shader)
        self.__slide.unif[47] = self.__edge_alpha
        self.__slide.unif[54] = float(self.__blend_type)
        self.__slide.unif[55] = 1.0  # brightness
        
        # Initialize texture uniforms to defaults (Scale=1.0, Offset=0.0) to prevent artifacts
        # tex0 (FG)
        self.__slide.unif[42] = 1.0; self.__slide.unif[43] = 1.0
        self.__slide.unif[48] = 0.0; self.__slide.unif[49] = 0.0
        self.__slide.unif[50] = 1.0 # Scale/Mix tex0
        # tex1 (BG)
        self.__slide.unif[45] = 1.0; self.__slide.unif[46] = 1.0
        self.__slide.unif[51] = 0.0; self.__slide.unif[52] = 0.0
        self.__slide.unif[53] = 1.0 # Scale/Mix tex1
        
        self.__textblocks = [None, None]
        
        # Use uv_flat for images to allow simple alpha blending of two separate sprites
        self.__flat_shader = pi3d.Shader("uv_flat") 
        self.__slide.set_shader(self.__flat_shader)
        # Place background sprite further back (z=10.0) to avoid z-fighting with foreground (z=5.0)
        self.__slide_bg = pi3d.Sprite(camera=camera, w=1.0, h=1.0, z=10.0)
        self.__slide_bg.set_shader(self.__flat_shader)
        
        # Load Icons
        try:
            if self.__icon_path:
                self.__logger.debug(f"Looking for icons in: {self.__icon_path}")
                play_file = os.path.join(self.__icon_path, 'play.png')
                pause_file = os.path.join(self.__icon_path, 'pause.png')
                skipf_file = os.path.join(self.__icon_path, 'skipf.png')
                download_file = os.path.join(self.__icon_path, 'download.png')
                offline_file = os.path.join(self.__icon_path, 'offline.png')
                sync_file = os.path.join(self.__icon_path, 'sync.png')
                nowlan_file = os.path.join(self.__icon_path, 'nowlan.png')
                eject_file = os.path.join(self.__icon_path, 'eject.png')
                if os.path.exists(play_file):
                    self.__icon_play = pi3d.Texture(play_file, blend=True, mipmap=False)
                if os.path.exists(pause_file):
                    self.__icon_pause = pi3d.Texture(pause_file, blend=True, mipmap=False)
                if os.path.exists(skipf_file):
                    self.__icon_skipf = pi3d.Texture(skipf_file, blend=True, mipmap=False)
                if os.path.exists(download_file):
                    self.__icon_download = pi3d.Texture(download_file, blend=True, mipmap=False)
                if os.path.exists(offline_file):
                    self.__icon_offline = pi3d.Texture(offline_file, blend=True, mipmap=False)
                if os.path.exists(sync_file):
                    self.__icon_sync = pi3d.Texture(sync_file, blend=True, mipmap=False)
                if os.path.exists(nowlan_file):
                    self.__icon_nowlan = pi3d.Texture(nowlan_file, blend=True, mipmap=False)
                if os.path.exists(eject_file):
                    self.__icon_eject = pi3d.Texture(eject_file, blend=True, mipmap=False)
            
            if self.__icon_play or self.__icon_pause or self.__icon_skipf or self.__icon_download or \
               self.__icon_offline or self.__icon_sync or self.__icon_nowlan or self.__icon_eject:
                # Create sprite with unit size, will be scaled to texture size in __draw_clock
                self.__icon_sprite = pi3d.Sprite(camera=camera, w=1.0, h=1.0, z=4.0)
                self.__icon_sprite.set_shader(self.__flat_shader)
        except Exception as e:
            self.__logger.warning(f"Could not load icons: {e}")

        self.__sfg = None # Reset foreground texture after display re-initialization
        self.__sbg = None # Reset background texture after display re-initialization
        self.__skip_draw = True # Set flag to skip first draw call after re-initialization

        if self.__text_bkg_hgt:
            bkg_hgt = int(min(self.__display.width, self.__display.height) * self.__text_bkg_hgt)
            text_bkg_array = np.zeros((bkg_hgt, 1, 4), dtype=np.uint8)
            text_bkg_array[:, :, 3] = np.linspace(0, 120, bkg_hgt).reshape(-1, 1)
            text_bkg_tex = pi3d.Texture(text_bkg_array, blend=True, mipmap=False, free_after_load=True)
            self.__text_bkg = pi3d.Sprite(w=self.__display.width,
                                          h=bkg_hgt, y=-int(self.__display.height) // 2 + bkg_hgt // 2, z=4.0)
            self.__text_bkg.set_draw_details(self.__flat_shader, [text_bkg_tex])



    def slideshow_is_running(self, pics: Optional[List[Optional[get_image_meta.GetImageMeta]]] = None,
                             time_delay: float = 200.0, fade_time: float = 10.0,
                             paused: bool = False) -> Tuple[bool, bool, bool]:
        self.__paused = paused
        # This method is now only for displaying images. Video playback is handled
        # by the controller calling play_video_blocking() directly.

        loop_running = self.__display.loop_running()
        if not loop_running:
            return (False, False, False)

        # Ensure we are using the flat shader for image slideshows (2-sprite system)
        if self.__slide.shader != self.__flat_shader:
             self.__slide.set_shader(self.__flat_shader)
             self.__slide_bg.set_shader(self.__flat_shader)

        if self.__background_sprite:
            self.__background_sprite.draw()

        tm = time.time()
        if pics is not None and pics[0] is not None:
            # Synchronous loading: This blocks the loop until the image is ready.
            # The current image remains static on screen during this time.
            
            # Check system status flags only once per image load for performance
            if os.path.exists("/dev/shm/picframe_no_files.flag"):
                self.__system_state = "eject"
            elif os.path.exists("/dev/shm/picframe_offline.flag"):
                self.__system_state = "offline"
            elif os.path.exists("/dev/shm/picframe_nowlan.flag"):
                self.__system_state = "nowlan"
            elif os.path.exists("/dev/shm/picframe_download.flag"):
                self.__system_state = "download"
            elif os.path.exists("/dev/shm/picframe_scanning.flag"):
                self.__system_state = "sync"
            else:
                self.__system_state = None

            new_sfg = self.__tex_load_sync(pics, (self.__display.width, self.__display.height))
            
            if new_sfg:
                self.__logger.info(f"Transitioning for {fade_time} sec")

                if self.__kenburns and self.__kb_current_state:
                    self.__kb_previous_state = self.__kb_current_state.copy()

                self.__textblocks = [None, None]
                if self.__show_text_tm > 0.0:
                    for i, pic in enumerate(pics):
                        self.__make_text(pic, paused, i, pics[1] is not None)

                # Reset time base to NOW, so the display time starts counting AFTER loading is done
                
                if self.__sfg is None:
                    self.__logger.info("Previous image was None (First run or reset). Starting with alpha 1.0.")
                    self.__alpha = 1.0
                    self.__sbg = new_sfg
                    self.__slide_bg.set_textures([new_sfg])
                else:
                    self.__alpha = 0.0
                    self.__sbg = self.__sfg
                    
                    # COPY GEOMETRY from __slide to __slide_bg
                    # This ensures the background sprite starts exactly where the foreground sprite was,
                    # preventing any "jumps" or hard cuts if the state calculation differs slightly.
                    # pi3d Shape uniforms: 0-2 pos, 3-5 rot, 6-8 scale
                    for i in range(9):
                        self.__slide_bg.unif[i] = self.__slide.unif[i]
                    
                    # Push background slightly further back (Z=10) to avoid Z-fighting, 
                    # but keep X/Y/Scale exactly as they were.
                    self.__slide_bg.position(self.__slide.unif[0], self.__slide.unif[1], 10.0)
                
                self.__sfg = new_sfg
                
                self.__logger.debug("Setting textures: __sfg=%s, __sbg=%s", self.__sfg, self.__sbg)
                
                self.__slide.set_textures([self.__sfg])
                self.__slide_bg.set_textures([self.__sbg])

                # Calculate Ken Burns state (after text, before timestamps)
                if self.__kenburns:
                    self.__kb_current_state = self.__calculate_kenburns_transform(self.__sfg, time_delay)

                # Force garbage collection to prevent stalls during transition
                gc.collect()

                # Update timestamps AFTER uploading textures and calculations to ensure transition starts exactly NOW
                tm = time.time()
                self.__transition_start_tm = tm
                self.__next_tm = tm + time_delay
                self.__name_tm = tm + fade_time + self.__show_text_tm
                
                if self.__kenburns:
                    self.__kb_current_state['start_time'] = tm
                    self.__apply_kenburns_transform(self.__slide, self.__kb_current_state, 0.0)
                    
                    # Only recalculate background position if we didn't just copy it from a valid previous slide
                    if self.__sbg is None or self.__alpha == 1.0:
                        if self.__kb_previous_state:
                             elapsed = tm - self.__kb_previous_state.get('start_time', tm)
                             self.__apply_kenburns_transform(self.__slide_bg, self.__kb_previous_state, elapsed)
                        else:
                             # Fallback: Scale to display size if no KB state (e.g. after video or reset)
                             self.__slide_bg.scale(self.__display.width, self.__display.height, 1.0)
                             self.__slide_bg.position(0, 0, 10.0)
            else:
                return (loop_running, True, False) # Signal skip_file

        # This block handles the fade transition and Ken Burns effect for every frame
        if self.__alpha < 1.0:
            if fade_time > 0.5:
                self.__alpha = (tm - self.__transition_start_tm) / fade_time
            else:
                self.__alpha = 1.0
            if self.__alpha > 1.0:
                self.__alpha = 1.0
        
        # Check for transition completion
        if self.__was_in_transition and self.__alpha >= 1.0:
             actual_fade = tm - self.__transition_start_tm
             self.__logger.info(f"Transition done: Fade={actual_fade:.2f}s/{fade_time:.2f}s, Load={self.__last_load_time:.2f}s (Resize={self.__last_resize_time:.2f}s)")
             self.__was_in_transition = False
        
        if self.__alpha < 1.0:
             self.__was_in_transition = True

        # Apply Ken Burns transforms to both sprites independently
        if self.__kenburns:
            if self.__kb_previous_state and self.__alpha < 1.0:
                 elapsed = tm - self.__kb_previous_state.get('start_time', tm)
                 self.__apply_kenburns_transform(self.__slide_bg, self.__kb_previous_state, elapsed)
            
            if self.__kb_current_state:
                 elapsed = tm - self.__kb_current_state.get('start_time', tm)
                 self.__apply_kenburns_transform(self.__slide, self.__kb_current_state, elapsed)

        # Calculate smooth alpha for the foreground sprite
        smooth_alpha = self.__alpha * self.__alpha * (3.0 - 2.0 * self.__alpha)

        self.__logger.debug(f"alpha={self.__alpha:.2f}, next_tm-tm={(self.__next_tm - tm):.2f}, fade_time={fade_time:.2f}")
        if (self.__next_tm - tm) < fade_time or self.__alpha < 1.0:
            self.__in_transition = True
        else:
            self.__in_transition = False
        # Absolute safeguard: Do not attempt to draw if textures are not ready,
        # which can happen in the first frame after a video or when a new image has just been loaded.
        # This gives pi3d one full frame to process the new texture.
        if self.__skip_draw:
            self.__logger.debug("Safeguard triggered (skip_draw=True), skipping draw call for one frame.")
            self.__skip_draw = False # Reset the flag for the next frame
            return (loop_running, False, False)

        # Draw Background Sprite (Old Image) - Fading Out
        # This fades the entire old image out, solving the "ghosting" issue
        # in pillarbox/letterbox areas.
        self.__slide_bg.set_alpha(1.0 - smooth_alpha)
        self.__slide_bg.draw()

        # Draw Foreground Sprite (New Image) - Fading In
        self.__slide.set_alpha(smooth_alpha)
        self.__slide.draw()
        
        self.__draw_overlay()
        if self.clock_is_on:
            self.__draw_clock()
        self.__draw_icon()

        # Draw New Text
        if tm < self.__name_tm:
            if self.__show_text_tm > 0:
                dt = 1.0 - (self.__name_tm - tm) / self.__show_text_tm
            else:
                dt = 1.0
            if dt > 0.995: dt = 1.0
            ramp_pt = max(4.0, self.__show_text_tm / 4.0)
            alpha = max(0.0, min(1.0, ramp_pt * (1.0 - abs(1.0 - 2.0 * dt))))

            for block in self.__textblocks:
                if block is not None: block.sprite.set_alpha(alpha)

            if self.__text_bkg_hgt and any(block is not None for block in self.__textblocks):
                self.__text_bkg.set_alpha(alpha)
                self.__text_bkg.draw()

            for block in self.__textblocks:
                if block is not None: block.sprite.draw()
        
        return (loop_running, False, False)

    def __calculate_kenburns_transform(self, texture, duration):
        state = {'duration': duration}
        if not self.__kenburns or not texture or texture.ix == 0 or texture.iy == 0:
            return state

        # Use viewport aspect ratio
        display_aspect = self.__viewport_ar
        image_aspect = texture.ix / texture.iy
        is_portrait = image_aspect < display_aspect
        is_panorama = image_aspect > self.__screen_ar

        # Defaults
        start_zoom = 1.0
        end_zoom = 1.0
        
        # Pan is now relative to the "overshoot" (how much the sprite is larger than screen)
        # -1.0 = Full Left/Top, 1.0 = Full Right/Bottom
        start_pan_x = 0.0
        end_pan_x = 0.0
        start_pan_y = 0.0
        end_pan_y = 0.0

        if is_portrait:
            # PORTRAIT: Scroll
            # Zoom: Constant 1.0 (plus wobble if enabled)
            # Pan Y: -1.0 -> 1.0 (Top to Bottom) or vice versa
            
            start_zoom = 1.0
            end_zoom = 1.0

            scroll_dir = self.__kb_portrait_scroll_direction
            if scroll_dir == 'random':
                scroll_dir = random.choice(['up', 'down'])
            
            # Add random start/end offsets based on border_pct
            border_fraction = self.__kb_portrait_border_pct / 100.0
            max_offset = 2.0 * border_fraction # Total pan range is 2.0 (-1 to 1)

            if scroll_dir == 'down':  # Top to Bottom
                start_pan_y = random.uniform(-1.0, -1.0 + max_offset)
                end_pan_y = random.uniform(1.0 - max_offset, 1.0)
            else:  # Bottom to Top
                start_pan_y = random.uniform(1.0 - max_offset, 1.0)
                end_pan_y = random.uniform(-1.0, -1.0 + max_offset)

            zoom_pct = 0.0
            if self.__kb_random_pan:
                # Add zoom to allow for X-wobble without black bars
                zoom_pct = self.__kb_portrait_wobble_pct
                zoom_factor = 1.0 + (self.__kb_portrait_wobble_pct / 100.0)
                start_zoom = zoom_factor
                end_zoom = zoom_factor
                
                # Use full available slack for wobble
                start_pan_x = random.uniform(-1.0, 1.0)
                end_pan_x = random.uniform(-1.0, 1.0)
            
            # Calculate scroll info for logging
            scroll_info = ""
            vp_w, vp_h = self.__get_viewport_size()
            if vp_w > 0 and vp_h > 0:
                 geo_w = vp_w * start_zoom
                 geo_h = (vp_w / image_aspect) * start_zoom
                 effective_geo_h = geo_h
                 if self.__portrait_crop_ar:
                     virtual_geo_h = geo_w / self.__portrait_crop_ar
                     effective_geo_h = min(geo_h, virtual_geo_h)
                 scroll_range = max(0, effective_geo_h - vp_h)
                 usage_pct = (effective_geo_h / geo_h) * 100.0
                 
                 travel_fraction = abs(end_pan_y - start_pan_y) / 2.0
                 actual_px = travel_fraction * scroll_range
                 scroll_info = f", Range: {scroll_range:.0f}px (Crop: {usage_pct:.0f}%), Travel: {actual_px:.0f}px"

            self.__logger.info(f"KB Portrait: Scroll {scroll_dir}, Zoom {zoom_pct:.2f}% (Wobble), Pan X: {start_pan_x:.3f} -> {end_pan_x:.3f}, Pan Y: {start_pan_y:.3f} -> {end_pan_y:.3f}{scroll_info}")

        elif is_panorama:
            # PANORAMA: Scroll Horizontal
            
            # Zoom
            min_zoom_pct = min(2.0, self.__kb_panorama_zoom_pct * 0.2) # at least 2% or 20% of max
            zoom_pct = random.uniform(min_zoom_pct, self.__kb_panorama_zoom_pct)
            zoom_factor = 1.0 + (zoom_pct / 100.0)
            
            zoom_dir = self.__kb_panorama_zoom_direction
            if zoom_dir == "random":
                zoom_dir = random.choice(["in", "out"])
            
            if zoom_dir == "in":
                start_zoom = 1.0
                end_zoom = zoom_factor
            else:
                start_zoom = zoom_factor
                end_zoom = 1.0

            # Scroll
            scroll_dir = self.__kb_panorama_scroll_direction
            if scroll_dir == 'random':
                scroll_dir = random.choice(['left', 'right'])
            
            if scroll_dir == 'right': # Left to Right (Viewport moves right)
                start_pan_x = -1.0
                end_pan_x = 1.0
            else: # Right to Left (Viewport moves left)
                start_pan_x = 1.0
                end_pan_x = -1.0
            
            # No vertical wobble for panoramas
            start_pan_y = 0.0
            end_pan_y = 0.0
            self.__logger.info(f"KB Panorama: Scroll {scroll_dir}, Zoom {zoom_dir} {zoom_pct:.2f}%")

        else:
            # LANDSCAPE: Zoom
            direction = self.__kb_landscape_zoom_direction
            if direction == "random":
                direction = random.choice(["in", "out"])

            # Randomize zoom percentage for each image
            # Ensure a minimum zoom to make the effect visible (at least 30% of max or 5%, whichever is smaller)
            min_zoom = min(5.0, self.__kb_landscape_zoom_pct * 0.3)
            zoom_pct = random.uniform(min_zoom, self.__kb_landscape_zoom_pct)
            zoom_factor = 1.0 + (zoom_pct / 100.0)
            
            # Wobble range
            wobble_range = self.__kb_landscape_wobble_pct / 100.0

            if direction == "in":
                start_zoom = 1.0
                end_zoom = zoom_factor
                
                # Start centered (0.0), End with wobble
                if self.__kb_random_pan:
                    end_pan_x = random.uniform(-wobble_range, wobble_range)
                    end_pan_y = random.uniform(-wobble_range, wobble_range)
                
                self.__logger.info(f"KB Landscape: Zoom IN {zoom_pct:.2f}%, End Pan: ({end_pan_x:.3f}, {end_pan_y:.3f})")
            
            else: # out
                start_zoom = zoom_factor
                end_zoom = 1.0
                
                # Start with wobble, End centered (0.0)
                if self.__kb_random_pan:
                    start_pan_x = random.uniform(-wobble_range, wobble_range)
                    start_pan_y = random.uniform(-wobble_range, wobble_range)
                
                self.__logger.info(f"KB Landscape: Zoom OUT {zoom_pct:.2f}%, Start Pan: ({start_pan_x:.3f}, {start_pan_y:.3f})")

        state['start_zoom'] = start_zoom
        state['end_zoom'] = end_zoom
        state['start_pan_x'] = start_pan_x
        state['end_pan_x'] = end_pan_x
        state['start_pan_y'] = start_pan_y
        state['end_pan_y'] = end_pan_y
        
        return state

    def __apply_kenburns_transform(self, sprite, state, elapsed_time):
        if not state or state.get('duration', 0) <= 0:
            return

        t = min(1.0, max(0.0, elapsed_time / state['duration']))
        t = t * t * (3.0 - 2.0 * t) # ease-in-out

        zoom = state['start_zoom'] + t * (state['end_zoom'] - state['start_zoom'])
        pan_x = state['start_pan_x'] + t * (state['end_pan_x'] - state['start_pan_x'])
        pan_y = state['start_pan_y'] + t * (state['end_pan_y'] - state['start_pan_y'])
        
        # Get texture from the specific sprite
        texture = sprite.buf[0].textures[0] if sprite.buf[0].textures else None
        if not texture:
            return

        # Calculate Aspect Fill Dimensions (Geometry)
        # We scale the sprite so the image fills the viewport perfectly.
        display_aspect = self.__viewport_ar
        image_aspect = texture.ix / texture.iy if texture.iy > 0 else 1.0
        
        vp_w, vp_h = self.__get_viewport_size()
        
        if display_aspect > image_aspect:
            # Portrait image on Landscape screen (or narrower on wider)
            # Fit Width, Crop Height
            # Sprite Width = Viewport Width
            # Sprite Height = Viewport Width / Image AR (This will be > Viewport Height)
            geo_w = vp_w
            geo_h = vp_w / image_aspect
        else:
            # Landscape image on Portrait screen (or wider on narrower)
            # Fit Height, Crop Width
            geo_h = vp_h
            geo_w = vp_h * image_aspect

        # Apply Zoom to Geometry
        # Zooming IN means making the sprite LARGER
        geo_w *= zoom
        geo_h *= zoom
        
        # Apply Pan to Geometry (Move the sprite)
        # Calculate max shift allowed (overshoot)
        max_x = max(0, (geo_w - vp_w) / 2.0)
        
        # Calculate max_y with optional virtual crop for portrait
        effective_geo_h = geo_h
        if self.__portrait_crop_ar and display_aspect > image_aspect:
             virtual_geo_h = geo_w / self.__portrait_crop_ar
             effective_geo_h = min(geo_h, virtual_geo_h)
             
        max_y = max(0, (effective_geo_h - vp_h) / 2.0)
        
        pos_x = pan_x * max_x
        pos_y = pan_y * max_y
        
        # Update Sprite Geometry
        sprite.scale(geo_w, geo_h, 1.0)
        
        # Use different Z-depths to avoid Z-fighting during transitions
        z_pos = 10.0 if sprite == self.__slide_bg else 5.0
        sprite.position(pos_x, pos_y, z_pos)

        # Log only for the foreground sprite (self.__slide) to avoid log spam
        if sprite == self.__slide:
             mode = "Portrait" if display_aspect > image_aspect else "Landscape"
             self.__logger.debug("KB: %s | vp=%.1fx%.1f sprite=%.1fx%.1f pos=%.1f,%.1f zoom=%.3f max_y=%.1f pan_y=%.2f eff_h=%.1f", 
                                 mode, vp_w, vp_h, geo_w, geo_h, pos_x, pos_y, zoom, max_y, pan_y, effective_geo_h)
    
    def slideshow_stop(self):
        if self.__display:
            self.__display.destroy()
        self.__clock_overlay = None
        self.__sfg = None # Ensure foreground texture is reloaded
        self.__sbg = None # Ensure background texture is reloaded

    def show_one_image_and_exit(self, pic, duration):
        """Creates a display, shows a single image for a duration, and then exits."""
        self.__logger.info(f"Displaying single image {pic.fname} for {duration}s")
        self.slideshow_start() # Creates display, shaders, etc.

        tex = self.__tex_load_sync([pic, None], size=(self.__display.width, self.__display.height))
        if tex is None:
            self.__logger.error("Failed to load texture for single image display.")
            self.slideshow_stop()
            return

        # Set texture and reset alpha for a static display (no transition)
        self.__slide.set_textures([tex, tex])
        self.__slide.unif[44] = 1.0 # alpha = 1.0

        start_time = time.time()
        while self.__display.loop_running() and (time.time() - start_time < duration):
            self.__slide.draw()
            # Minimal sleep to keep CPU usage reasonable
            time.sleep(0.01)
        
        self.slideshow_stop() # Destroys display


    def play_video(self, video_path: str):
        self.__logger.info("Video file detected. Preparing for external player.")
        
        def _blank_screen():
            """Blanks the screen by writing zeros to the framebuffer."""
            try:
                # Using a simple dd command to write zeros is a robust way to get a black screen.
                command = ["dd", "if=/dev/zero", "of=/dev/fb0", "bs=1M"]
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.__logger.debug("Screen blanked successfully.")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.__logger.warning(f"Could not blank screen using dd: {e}")

        # --- Step 1: Stop pi3d cleanly ---
        if self.__display:
            self.slideshow_stop() # This destroys the display

        # --- Step 2: Blank the screen BEFORE video starts ---
        _blank_screen()

        # --- Step 3: Play the video (blocking call) ---
        self.__logger.info(f"Starting mpv for: {video_path}")
        try:
            command = ["mpv", "--no-config", "--fullscreen", "--really-quiet", video_path]
            subprocess.run(command, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.__logger.error(f"Error during video playback with mpv: {e}")

        self.__logger.info("Video playback finished.")
        # --- Step 4: Blank the screen AGAIN after video finishes ---
        _blank_screen()

    def play_video_slideshow(self, pic, video_extractor: VideoExtractor, fade_time: float, time_delay: float):
        video_path = pic.fname
        self.__video_slideshow_playing = True
        try:
            self.__logger.info(f"Starting video slideshow (ffmpeg) for: {video_path}. Fade={fade_time}, Delay={time_delay}")
            
            # Prepare text overlay using the standard method
            self.__make_text(pic, False)
            self.__name_tm = 0.0 # Initialize to 0 so text doesn't show during pre-roll/fade-in

            def draw_overlays():
                self.__draw_overlay()
                if self.clock_is_on:
                    self.__draw_clock()
                self.__draw_icon()
                
                tm = time.time()
                if tm < self.__name_tm:
                    if self.__show_text_tm > 0:
                        dt = 1.0 - (self.__name_tm - tm) / self.__show_text_tm
                    else:
                        dt = 1.0
                    if dt > 0.995: dt = 1.0
                    ramp_pt = max(4.0, self.__show_text_tm / 4.0)
                    alpha = max(0.0, min(1.0, ramp_pt * (1.0 - abs(1.0 - 2.0 * dt))))

                    for block in self.__textblocks:
                        if block is not None: block.sprite.set_alpha(alpha)

                    if self.__text_bkg_hgt and any(block is not None for block in self.__textblocks):
                        self.__text_bkg.set_alpha(alpha)
                        self.__text_bkg.draw()

                    for block in self.__textblocks:
                        if block is not None: block.sprite.draw()
            
            frames_dir = video_extractor.get_frames_dir(video_path)
            
            def get_frame_path(i):
                return frames_dir / f"frame_{i:04d}.jpg"

            # Wait for first frames
            wait_start = time.time()
            required_frames = 3
            while not get_frame_path(required_frames).exists():
                if time.time() - wait_start > 120: # Timeout increased for Pi Zero
                    if get_frame_path(2).exists():
                        self.__logger.warning(f"Timeout waiting for {required_frames} frames. Starting with available frames.")
                        break
                    self.__logger.warning("Timeout waiting for video frames.")
                    return
                
                # Check if extractor has finished (failed or done) without producing frames
                if not video_extractor.is_in_process(video_path):
                    # If finished, check if we at least have the first frame
                    if get_frame_path(1).exists():
                        self.__logger.info("Video extraction finished early. Starting slideshow with available frames.")
                        break
                    else:
                        self.__logger.warning("Video extraction process stopped without producing required frames.")
                        return

                if not self.__display.loop_running():
                    self.__logger.info("Display loop stopped while waiting for video frames.")
                    print("DEBUG: Display loop stopped inside play_video_slideshow (waiting for frames).")
                    return
                
                # Draw previous image while waiting to avoid black screen freeze
                if self.__sfg:
                    # Keep using the existing shader/geometry (Ken Burns state) to avoid glitches
                    self.__slide.draw()
                    draw_overlays()
                else:
                    # If no previous image exists (start of app), draw black to keep loop alive
                    # Switch to blend shader to safely draw "nothing" (alpha 0)
                    if self.__slide.shader != self.__blend_shader:
                        self.__slide.set_shader(self.__blend_shader)
                    
                    self.__slide.unif[44] = 0.0 # Alpha 0
                    self.__slide.draw()
                    draw_overlays()
                time.sleep(0.05) # Reduce CPU usage while waiting

            tex_b = pi3d.Texture(str(get_frame_path(1)), blend=True, m_repeat=False, mipmap=False, free_after_load=True)
            self.__logger.info(f"First frame loaded. Resolution: {tex_b.ix}x{tex_b.iy}")
            
            # --- Transition Logic: Photo -> Video ---
            # 1. Setup Background (Old Image) to freeze it in place
            if self.__sfg:
                self.__slide_bg.set_shader(self.__flat_shader)
                self.__slide_bg.set_textures([self.__sfg])
                
                if self.__kenburns and self.__kb_current_state:
                    # Apply the final state of the Ken Burns effect to freeze the image
                    duration = self.__kb_current_state.get('duration', 100.0)
                    self.__apply_kenburns_transform(self.__slide_bg, self.__kb_current_state, duration)
                else:
                    # Fallback: Scale to display size if no KB state
                    self.__slide_bg.scale(self.__display.width, self.__display.height, 1.0)
                    self.__slide_bg.position(0, 0, 10.0)
                
                self.__slide_bg.set_alpha(1.0)

            # 2. Setup Foreground (New Video Frame) - Full Screen
            self.__slide.set_shader(self.__flat_shader)
            self.__slide.set_textures([tex_b])
            self.__slide.scale(self.__display.width, self.__display.height, 1.0)
            self.__slide.position(0, 0, 5.0)
            
            # 3. Execute Cross-Fade
            if self.__sfg:
                self.__slide.set_alpha(0.0)
                start_time = time.time()
                while True:
                    t = time.time() - start_time
                    if t > fade_time: break
                    if not self.__display.loop_running(): return
                    
                    blend = t / fade_time
                    self.__slide_bg.set_alpha(1.0 - blend)
                    self.__slide.set_alpha(blend)
                    
                    self.__slide_bg.draw()
                    self.__slide.draw()
                    draw_overlays()
                self.__slide_bg.set_alpha(0.0)
            
            self.__slide.set_alpha(1.0)

            # --- Video Slideshow Loop Setup ---
            # Now switch to blend shader for the internal video slideshow loop
            self.__slide.set_shader(self.__blend_shader)
            
            # Reset background sprite geometry for future use
            self.__slide_bg.scale(self.__display.width, self.__display.height, 1.0)
            self.__slide_bg.position(0, 0, 10.0)
            
            # Setup slide for slideshow mode
            self.__slide.unif[55] = 1.0 # Brightness
            self.__slide.unif[54] = 0.0 # Mix mode
            self.__slide.unif[47] = 1.0 # Edge alpha
            
            # Reset all texture scaling and offsets to defaults
            self.__slide.unif[42] = 1.0; self.__slide.unif[43] = 1.0
            self.__slide.unif[45] = 1.0; self.__slide.unif[46] = 1.0
            self.__slide.unif[48] = 0.0; self.__slide.unif[49] = 0.0
            self.__slide.unif[51] = 0.0; self.__slide.unif[52] = 0.0
            self.__slide.unif[50] = 1.0; self.__slide.unif[53] = 1.0
            
            # Setup textures for blend loop (both slots point to current frame initially)
            self.__slide.set_draw_details(self.__slide.shader, [tex_b, tex_b])
            self.__slide.unif[44] = 0.0 
            
            # Start showing text now that the video frames are visible
            self.__name_tm = time.time() + self.__show_text_tm
            
            current_idx = 1
            ffmpeg_paused = False
            stats_hold = []
            stats_wait = []
            stats_blend = []
            
            while True:
                # 1. Hold current frame
                start_time = time.time()
                while (time.time() - start_time) < time_delay:
                    if not self.__display.loop_running():
                        if ffmpeg_paused: video_extractor.resume()
                        return
                    self.__slide.draw()
                    draw_overlays()
                actual_hold = time.time() - start_time
                stats_hold.append(actual_hold)

                # 2. Prepare next frame
                wait_start = time.time()
                next_idx = current_idx + 1
                next_path = get_frame_path(next_idx)
                lookahead_path = get_frame_path(next_idx + 1)
                
                while not lookahead_path.exists():
                    # If we are waiting for frames and ffmpeg is paused, resume it!
                    if ffmpeg_paused:
                        video_extractor.resume()
                        ffmpeg_paused = False

                    # Check if extraction is finished (no more frames coming)
                    if not video_extractor.is_in_process(video_path):
                        if not next_path.exists():
                            # End of video
                            # Clean up temp dir for this video
                            try:
                                shutil.rmtree(frames_dir)
                            except Exception:
                                pass
                            # Keep the last texture as sfg for the next image transition
                            self.__logger.info(f"Video slideshow finished. Total frames shown: {current_idx}")
                            if stats_wait:
                                avg_wait = sum(stats_wait) / len(stats_wait)
                                avg_hold = sum(stats_hold) / len(stats_hold)
                                avg_blend = sum(stats_blend) / len(stats_blend)
                                self.__logger.info(f"Stats: Avg Wait={avg_wait:.2f}s, Avg Hold={avg_hold:.2f}s, Avg Blend={avg_blend:.2f}s")
                            self.__sfg = tex_b
                            self.__sbg = None
                            
                            # Prepare sprite for static display until next image loads
                            self.__slide.set_textures([tex_b])
                            self.__slide.unif[44] = 1.0 # Ensure full opacity
                            
                            # Clear Ken Burns state to prevent previous image's transform from applying to this static frame
                            if self.__kenburns:
                                self.__kb_current_state = {}
                                self.__kb_previous_state = {}
                            
                            return
                        else:
                            # Next frame exists, but lookahead doesn't. This is the last frame.
                            break
                    
                    if not self.__display.loop_running():
                        if ffmpeg_paused: video_extractor.resume()
                        return
                    self.__slide.draw()
                    draw_overlays()
                    time.sleep(0.05)
                actual_wait = time.time() - wait_start
                stats_wait.append(actual_wait)

                tex_f = tex_b
                tex_b = pi3d.Texture(str(next_path), blend=True, m_repeat=False, mipmap=False, free_after_load=True)
                
                self.__slide.set_draw_details(self.__slide.shader, [tex_f, tex_b])
                self.__slide.unif[44] = 1.0
                
                # 3. Blend
                start_time = time.time()
                while True:
                    t = time.time() - start_time
                    if t > fade_time: break
                    if not self.__display.loop_running():
                        if ffmpeg_paused: video_extractor.resume()
                        return
                    blend = t / fade_time
                    self.__slide.unif[44] = 1.0 - blend
                    self.__slide.draw()
                    draw_overlays()
                actual_blend = time.time() - start_time
                stats_blend.append(actual_blend)
                
                self.__slide.unif[44] = 0.0
                self.__slide.draw()
                draw_overlays()
                
                self.__logger.debug(f"Video Frame {current_idx}: Hold={actual_hold:.2f}s, Wait={actual_wait:.2f}s, Blend={actual_blend:.2f}s")
                
                # Throttling: Pause ffmpeg if too many frames are produced in advance
                if video_extractor.is_in_process(video_path):
                    # If 5 frames exist in advance -> Pause to save RAM/IO
                    if get_frame_path(current_idx + 5).exists() and not ffmpeg_paused:
                        video_extractor.pause()
                        ffmpeg_paused = True
                    # If only 2 frames exist in advance -> Continue
                    elif not get_frame_path(current_idx + 2).exists() and ffmpeg_paused:
                        video_extractor.resume()
                        ffmpeg_paused = False
                
                # 4. Cleanup old frame
                try:
                    os.remove(get_frame_path(current_idx))
                except OSError:
                    pass
                
                current_idx += 1
        finally:
            self.__video_slideshow_playing = False
