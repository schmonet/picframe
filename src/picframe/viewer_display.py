import time
import subprocess
import logging
import os
import random
from typing import Optional, List, Tuple
from datetime import datetime
from PIL import Image, ImageFilter, ImageFile
import numpy as np
import pi3d  # type: ignore
from picframe import mat_image, get_image_meta
from picframe.video_streamer import VideoStreamer, VIDEO_EXTENSIONS, VideoFrameExtractor

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
        self.__mat_type = config['mat_type']
        self.__outer_mat_color = config['outer_mat_color']
        self.__inner_mat_color = config['inner_mat_color']
        self.__outer_mat_border = config['outer_mat_border']
        self.__inner_mat_border = config['inner_mat_border']
        self.__outer_mat_use_texture = config['outer_mat_use_texture']
        self.__inner_mat_use_texture = config['inner_mat_use_texture']
        self.__mat_resource_folder = os.path.expanduser(config['mat_resource_folder'])

        self.__fps = config['fps']
        self.__background = config['background']
        self.__blend_type = {"blend": 0.0, "burn": 1.0, "bump": 2.0}[config['blend_type']]
        self.__font_file = os.path.expanduser(config['font_file'])
        self.__shader = os.path.expanduser(config['shader'])
        self.__show_text_tm = float(config['show_text_tm'])
        self.__show_text_fm = config['show_text_fm']
        self.__show_text_sz = config['show_text_sz']
        self.__show_text = parse_show_text(config['show_text'])
        self.__text_justify = config['text_justify'].upper()
        self.__text_wdt_offset_pct = config.get('text_wdt_offset_pct', 3.0)
        self.__text_bkg_hgt = config['text_bkg_hgt'] if 0 <= config['text_bkg_hgt'] <= 1 else 0.25
        self.__text_opacity = config['text_opacity']
        self.__fit = config['fit']
        self.__video_fit_display = config['video_fit_display']
        self.__geo_suppress_list = config['geo_suppress_list']
        self.__kenburns = config['kenburns']
        self.__crop_ar = None
        if 'crop_to_aspect_ratio' in config and config['crop_to_aspect_ratio']:
            try:
                w, h = map(float, config['crop_to_aspect_ratio'].split(':'))
                if h > 0: self.__crop_ar = w / h
            except Exception as e:
                self.__logger.warning("Could not parse crop_to_aspect_ratio: %s", e)

        if self.__kenburns:
            self.__kb_zoom_direction = config.get('kenburns_zoom_direction', 'random')
            self.__kb_scroll_direction = config.get('kenburns_scroll_direction', 'random')
            self.__kb_zoom_pct = abs(config.get('kenburns_zoom_pct', 10.0))
            self.__kb_landscape_wobble_pct = abs(config.get('kenburns_landscape_wobble_pct', 5.0))
            self.__kb_portrait_wobble_pct = abs(config.get('kenburns_portrait_wobble_pct', 5.0))
            self.__kb_random_pan = config.get('kenburns_random_pan', True)
            self.__kb_portrait_border_pct = abs(config.get('kenburns_portrait_border_pct', 20.0))
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
        self.__display = None
        self.__slide = None
        self.__flat_shader = None
        self.__textblocks = [None, None]
        self.__text_bkg = None
        self.__sfg = None  # slide for background
        self.__sbg = None  # slide for foreground
        self.__last_frame_tex = None  # slide for last frame of video
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
        self.__video_streamer = None
        self.__kmsblank_proc = None
        ImageFile.LOAD_TRUNCATED_IMAGES = True  # occasional damaged file hangs app

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

    def __tex_load(self, pics, size=None):
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
                    return None
                if pics[0].orientation != 1:
                    im = self.__orientate_image(im, pics[0])

            if self.__crop_ar is not None:
                image_ar = im.width / im.height
                if (image_ar / self.__crop_ar) > 1.01:
                    new_width = self.__crop_ar * im.height
                    left = (im.width - new_width) / 2
                    im = im.crop((left, 0, left + new_width, im.height))
                elif (self.__crop_ar / image_ar) > 1.01:
                    new_height = im.width / self.__crop_ar
                    top = (im.height - new_height) / 2
                    im = im.crop((0, top, im.width, top + new_height))

            if pics[1]:
                im2 = get_image_meta.GetImageMeta.get_image_object(pics[1].fname)
                if im2 is None:
                    return None
                if pics[1].orientation != 1:
                    im2 = self.__orientate_image(im2, pics[1])

            screen_aspect, image_aspect, diff_aspect = self.__get_aspect_diff(size, im.size)

            if self.__mat_images and diff_aspect > self.__mat_images_tol:
                if not pics[1]:
                    im = self.__matter.mat_image((im,))
                else:
                    im = self.__matter.mat_image((im, im2))
            else:
                if pics[1]:
                    im = self.__create_image_pair(im, im2)

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
            tex = pi3d.Texture(im, blend=True, m_repeat=False, free_after_load=True)
        except Exception as e:
            self.__logger.warning("Can't create tex from file: \"%s\" or \"%s\"", pics[0].fname, pics[1])
            self.__logger.warning("Cause: %s", e)
            tex = None
        return tex

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
            adj_x = (c_rng - block.sprite.width) // 2
            if self.__text_justify == "L":
                adj_x *= -1
            elif self.__text_justify == "C":
                adj_x = 0
            if side == 0 and not pair:
                x = adj_x
            else:
                x = adj_x + int(self.__display.width * 0.25 * (-1.0 if side == 0 else 1.0))
            y = (block.sprite.height - self.__display.height + self.__show_text_sz) // 2
            block.sprite.position(x, y, 0.1)
            block.sprite.set_alpha(0.0)
        if side == 0:
            self.__textblocks[1] = None
        self.__textblocks[side] = block

    def __draw_clock(self):
        current_time = datetime.now().strftime(self.__clock_format)
        if current_time != self.__prev_clock_time:
            wdt_offset = int(self.__display.width * self.__clock_wdt_offset_pct / 100)
            hgt_offset = int(self.__display.height * self.__clock_hgt_offset_pct / 100)
            width = self.__display.width - (wdt_offset * 2)
            clock_text = current_time
            if os.path.isfile("/dev/shm/clock.txt"):
                with open("/dev/shm/clock.txt", "r") as f:
                    clock_text = f.read()
                    clock_text = f"{current_time}\n{clock_text}"
            opacity = int(255 * float(self.__clock_opacity))
            self.__clock_overlay = pi3d.FixedString(self.__font_file, clock_text, font_size=self.__clock_text_sz,
                                                    shader=self.__flat_shader, width=width, shadow_radius=3,
                                                    justify=self.__clock_justify, color=(255, 255, 255, opacity))
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
            background=self.__background, use_glx=self.__use_glx,
            use_sdl2=self.__use_sdl2)
        camera = pi3d.Camera(is_3d=False)
        shader = pi3d.Shader(self.__shader)
        self.__slide = pi3d.Sprite(camera=camera, w=self.__display.width, h=self.__display.height, z=5.0)
        self.__slide.set_shader(shader)
        self.__slide.unif[47] = self.__edge_alpha
        self.__slide.unif[54] = float(self.__blend_type)
        self.__slide.unif[55] = 1.0  # brightness
        self.__textblocks = [None, None]
        self.__flat_shader = pi3d.Shader("uv_flat")

        if self.__text_bkg_hgt:
            bkg_hgt = int(min(self.__display.width, self.__display.height) * self.__text_bkg_hgt)
            text_bkg_array = np.zeros((bkg_hgt, 1, 4), dtype=np.uint8)
            text_bkg_array[:, :, 3] = np.linspace(0, 120, bkg_hgt).reshape(-1, 1)
            text_bkg_tex = pi3d.Texture(text_bkg_array, blend=True, mipmap=False, free_after_load=True)
            self.__text_bkg = pi3d.Sprite(w=self.__display.width,
                                          h=bkg_hgt, y=-int(self.__display.height) // 2 + bkg_hgt // 2, z=4.0)
            self.__text_bkg.set_draw_details(self.__flat_shader, [text_bkg_tex])

    def __load_video_frames(self, video_path: str) -> Optional[tuple[pi3d.Texture, pi3d.Texture]]:
        try:
            self.__logger.debug("Loading video frames: %s", video_path)
            extractor = VideoFrameExtractor(
                video_path, self.__display.width, self.__display.height, fit_display=self.__video_fit_display
            )
            frames = extractor.get_first_and_last_frames()
            if frames is not None:
                frame_first, frame_last = frames
                first_frame_tex = pi3d.Texture(frame_first, blend=True, m_repeat=False, free_after_load=True)
                last_frame_tex = pi3d.Texture(frame_last, blend=True, m_repeat=False, free_after_load=True)
                return first_frame_tex, last_frame_tex
            else:
                self.__logger.warning("Failed to retrieve frames from video: %s", video_path)
                return None
        except Exception as e:
            self.__logger.warning("Can't create video textures from file: %s", video_path)
            self.__logger.warning("Cause: %s", e)
            return None

    def slideshow_is_running(self, pics: Optional[List[Optional[get_image_meta.GetImageMeta]]] = None,
                             time_delay: float = 200.0, fade_time: float = 10.0,
                             paused: bool = False) -> Tuple[bool, bool, bool]:
        loop_running = self.__display.loop_running()
        video_playing = False
        if self.is_video_playing():
            self.pause_video(paused)
            video_playing = True
            if self.__last_frame_tex is not None:
                self.__sfg = self.__last_frame_tex
                self.__last_frame_tex = None
                self.__slide.set_textures([self.__sfg, self.__sbg])
            self.__slide.draw()
            return (loop_running, False, video_playing)

        tm = time.time()
        if pics is not None:
            if self.__kenburns and self.__kb_current_state:
                self.__kb_previous_state = self.__kb_current_state.copy()

            self.stop_video()
            if pics[0] and os.path.splitext(pics[0].fname)[1].lower() in VIDEO_EXTENSIONS:
                self.__video_path = pics[0].fname
                textures = self.__load_video_frames(self.__video_path)
                new_sfg = textures[0] if textures else None
                self.__last_frame_tex = textures[1] if textures else None
            else:
                new_sfg = self.__tex_load(pics, (self.__display.width, self.__display.height))

            if new_sfg is None:
                return (self.__display.loop_running(), True, False)

            tm = time.time()
            self.__next_tm = tm + time_delay
            self.__name_tm = tm + fade_time + self.__show_text_tm
            self.__sbg = self.__sfg
            self.__sfg = new_sfg
            self.__alpha = 0.0
            self.__delta_alpha = 1.0 / (self.__fps * fade_time) if fade_time > 0.5 else 1.0

            if self.__show_text_tm > 0.0:
                for i, pic in enumerate(pics):
                    self.__make_text(pic, paused, i, pics[1] is not None)
            else:
                for block in range(2):
                    self.__textblocks[block] = None

            if self.__sbg is None:
                self.__sbg = self.__sfg
            self.__slide.set_textures([self.__sfg, self.__sbg])
            
            if self.__kenburns:
                self.__kb_current_state = self.__calculate_kenburns_transform(self.__sfg, time_delay)
                self.__kb_current_state['start_time'] = tm # Set start time for the new animation
                self.__apply_kenburns_transform(self.__kb_current_state, 0.0, is_background=False)

        if self.__alpha < 1.0:
            self.__alpha += self.__delta_alpha
            if self.__alpha > 1.0:
                self.__alpha = 1.0
            
            if self.__kenburns and self.__kb_previous_state:
                elapsed = tm - self.__kb_previous_state.get('start_time', tm)
                self.__apply_kenburns_transform(self.__kb_previous_state, elapsed, is_background=True)

            if self.__kenburns and self.__kb_current_state:
                elapsed = tm - self.__kb_current_state.get('start_time', tm)
                self.__apply_kenburns_transform(self.__kb_current_state, elapsed, is_background=False)

        elif self.__kenburns and not paused and tm < self.__next_tm:
            elapsed = tm - self.__kb_current_state.get('start_time', tm)
            self.__apply_kenburns_transform(self.__kb_current_state, elapsed)

        self.__slide.unif[44] = self.__alpha * self.__alpha * (3.0 - 2.0 * self.__alpha)

        if (self.__next_tm - tm) < fade_time or self.__alpha < 1.0:
            self.__in_transition = True
        else:
            self.__in_transition = False
            if self.__video_path is not None and tm > self.__name_tm:
                if self.__video_streamer is None or not self.__video_streamer.player_alive():
                    self.__video_streamer = VideoStreamer(
                        self.__display_x, self.__display_y, self.__display.width, self.__display.height,
                        self.__video_path, fit_display=self.__video_fit_display)
                else:
                    self.__video_streamer.play(self.__video_path)
                self.__video_path = None

        self.__slide.draw()
        self.__draw_overlay()
        if self.clock_is_on:
            self.__draw_clock()

        if self.__alpha >= 1.0 and tm < self.__name_tm:
            if self.__show_text_tm > 0:
                dt = 1.0 - (self.__name_tm - tm) / self.__show_text_tm
            else:
                dt = 1
            if dt > 0.995: dt = 1
            ramp_pt = max(4.0, self.__show_text_tm / 4.0)
            alpha = max(0.0, min(1.0, ramp_pt * (1.0 - abs(1.0 - 2.0 * dt))))

            for block in self.__textblocks:
                if block is not None: block.sprite.set_alpha(alpha)

            if self.__text_bkg_hgt and any(block is not None for block in self.__textblocks):
                self.__text_bkg.set_alpha(alpha)
                self.__text_bkg.draw()

            for block in self.__textblocks:
                if block is not None: block.sprite.draw()
        return (loop_running, False, video_playing)

    def __calculate_kenburns_transform(self, texture, time_delay):
        state = {'duration': time_delay}
        if not self.__kenburns or not texture or texture.ix == 0 or texture.iy == 0:
            return state

        display_aspect = self.__display.width / self.__display.height
        image_aspect = texture.ix / texture.iy
        is_portrait = image_aspect < display_aspect

        x_start, x_end, y_start, y_end = 0.0, 0.0, 0.0, 0.0

        if is_portrait:
            # PORTRAIT: scroll effect
            scale = 1.0
            if self.__kb_random_pan:
                # Add a small zoom to prevent black bars during horizontal pan
                scale += self.__kb_portrait_wobble_pct / 100.0
            state['start_scale'] = scale
            state['end_scale'] = scale

            # Calculate vertical overshoot in pixels
            scaled_height = (self.__display.width / image_aspect) * scale
            overshoot_y = max(0, scaled_height - self.__display.height)
            max_pan_y = overshoot_y / 2.0

            # Randomize borders for start and end
            start_border = max_pan_y * (random.uniform(0, self.__kb_portrait_border_pct) / 100.0)
            end_border = max_pan_y * (random.uniform(0, self.__kb_portrait_border_pct) / 100.0)

            scroll_dir = self.__kb_scroll_direction
            if scroll_dir == 'random':
                scroll_dir = random.choice(['up', 'down'])

            # config 'down' = view 'top down' = image moves up = offset pos -> neg
            # config 'up' = view 'bottom up' = image moves down = offset neg -> pos
            if scroll_dir == 'down':
                y_start, y_end = max_pan_y - start_border, -max_pan_y + end_border
            else: # 'up'
                y_start, y_end = -max_pan_y + start_border, max_pan_y - end_border

            if self.__kb_random_pan:
                # Using display width for wobble range calculation is more intuitive for portrait
                wobble_range_x = (self.__display.width * self.__kb_portrait_wobble_pct / 100.0) / 2.0
                x_start = random.uniform(-wobble_range_x, wobble_range_x)
                x_end = random.uniform(-wobble_range_x, wobble_range_x)

        else: # LANDSCAPE: zoom effect
            direction = self.__kb_zoom_direction
            if direction == "random":
                direction = random.choice(["in", "out"])

            # Randomize zoom percentage for each image
            zoom_pct = random.uniform(0, self.__kb_zoom_pct)
            zoom_factor = 1.0 + (zoom_pct / 100.0)

            if direction == "in":
                state['start_scale'] = 1.0
                state['end_scale'] = zoom_factor
            else:  # out
                state['start_scale'] = zoom_factor
                state['end_scale'] = 1.0

            if self.__kb_random_pan:
                # Randomize pan magnitude for this image, relative to screen size
                pan_pct_x = random.uniform(0, self.__kb_landscape_wobble_pct)
                pan_pct_y = random.uniform(0, self.__kb_landscape_wobble_pct)

                # Calculate minimum scale to allow for the desired wobble, ensuring consistency
                min_scale_x = (display_aspect / image_aspect) * (1 + pan_pct_x / 100.0) if image_aspect > 0 else 1.0
                min_scale_y = 1 + pan_pct_y / 100.0
                min_scale_for_wobble = max(min_scale_x, min_scale_y)

                # Apply the minimum scale to the zoom animation
                state['start_scale'] = max(state['start_scale'], min_scale_for_wobble)
                state['end_scale'] = max(state['end_scale'], min_scale_for_wobble)

                # With the scale adjusted, the desired wobble is now always possible.
                desired_wobble_x = (self.__display.width * pan_pct_x / 100.0) / 2.0
                desired_wobble_y = (self.__display.height * pan_pct_y / 100.0) / 2.0

                x_start = random.uniform(-desired_wobble_x, desired_wobble_x)
                y_start = random.uniform(-desired_wobble_y, desired_wobble_y)
                x_end = random.uniform(-desired_wobble_x, desired_wobble_x)
                y_end = random.uniform(-desired_wobble_y, desired_wobble_y)

        state['start_offset_x'], state['end_offset_x'] = x_start, x_end
        state['start_offset_y'], state['end_offset_y'] = y_start, y_end

        self.__logger.debug("KB Setup: is_portrait=%s, scale=%.2f->%.2f, pan_x=%.2f->%.2f, pan_y=%.2f->%.2f",
            is_portrait, state.get('start_scale', 0), state.get('end_scale', 0), x_start, x_end, y_start, y_end)
        return state

    def __apply_kenburns_transform(self, state, elapsed_time, is_background=False):
        if not state or state.get('duration', 0) <= 0:
            return

        t = min(1.0, max(0.0, elapsed_time / state['duration']))
        t = t * t * (3.0 - 2.0 * t) # ease-in-out

        kb_scale = state['start_scale'] + t * (state['end_scale'] - state['start_scale'])
        offset_x = state['start_offset_x'] + t * (state['end_offset_x'] - state['start_offset_x'])
        offset_y = state['start_offset_y'] + t * (state['end_offset_y'] - state['start_offset_y'])

        texture = self.__sfg if not is_background else self.__sbg
        if not texture:
            return

        display_aspect = self.__display.width / self.__display.height
        image_aspect = texture.ix / texture.iy if texture.iy > 0 else 1.0

        # Base scaling to fit image without distortion
        if display_aspect > image_aspect: # Portrait on landscape
            scale_x = kb_scale
            scale_y = kb_scale * (display_aspect / image_aspect)
        else: # Landscape on portrait
            scale_x = kb_scale * (image_aspect / display_aspect)
            scale_y = kb_scale

        # Convert pixel offsets to shader's texture coordinate space
        offset_x_unif = (offset_x / self.__display.width) / scale_x if scale_x != 0 else 0
        offset_y_unif = (offset_y / self.__display.height) / scale_y if scale_y != 0 else 0

        if is_background:
            self.__slide.unif[45] = scale_x
            self.__slide.unif[46] = scale_y
            self.__slide.unif[50] = offset_x_unif
            self.__slide.unif[51] = offset_y_unif
        else:
            self.__slide.unif[42] = scale_x
            self.__slide.unif[43] = scale_y
            self.__slide.unif[48] = offset_x_unif
            self.__slide.unif[49] = offset_y_unif
    
    def stop_video(self):
        if self.__video_streamer is not None:
            self.__video_streamer.stop()

    def is_video_playing(self) -> bool:
        if self.__video_streamer is not None and self.__video_streamer.is_playing():
            return True
        return False

    def pause_video(self, do_pause: bool):
        if self.__video_streamer is not None:
            self.__video_streamer.pause(do_pause)

    def slideshow_stop(self):
        if self.__video_streamer is not None:
            self.__video_streamer.kill()
        self.__display.destroy()