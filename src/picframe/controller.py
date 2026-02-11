"""Controller of picframe."""

import logging
import time
import signal
import sys
import ssl
import os
import subprocess
from picframe.video_extractor import VideoExtractor
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v')


def make_date(txt):
    dt = (txt.replace('/', ':')
          .replace('-', ':')
          .replace(',', ':')
          .replace('.', ':')
          .split(':'))
    dt_tuple = tuple(int(i) for i in dt)
    return time.mktime(dt_tuple + (0, 0, 0, 0, 0, 0))


class Controller:
    """Controller of picframe."""

    def __init__(self, model, viewer):
        self.__logger = logging.getLogger("controller.Controller")
        self.__logger.info('creating an instance of Controller')
        self.__model = model
        self.__viewer = viewer
        self.__http_config = self.__model.get_http_config()
        self.__mqtt_config = self.__model.get_mqtt_config()
        self.__paused = False
        self.__force_navigate = False
        self.__next_tm = 0
        self.keep_looping = True
        self.__interface_peripherals = None
        self.__interface_mqtt = None
        self.__interface_http = None
        self.__video_extractor = None
        

    @property
    def paused(self):
        return self.__paused

    @paused.setter
    def paused(self, val: bool):
        self.__paused = val
        pic = self.__model.get_current_pics()[0]
        if pic:
            self.__viewer.reset_name_tm(pic, val, side=0, pair=self.__model.get_current_pics()[1] is not None)
        if self.__mqtt_config['use_mqtt']:
            self.publish_state()

    def next(self):
        self.__next_tm = 0
        self.__force_navigate = True
        self.__viewer.reset_name_tm()
        
    def back(self):
        self.__next_tm = 0
        self.__force_navigate = True
        self.__model.set_next_file_to_previous_file()
        self.__viewer.reset_name_tm()

    def delete(self):
        self.__next_tm = 0
        self.__model.delete_file()
        self.next()

    # ... (most property setters remain the same, just removing video specific logic)

    def loop(self):
        exit_code = 0 # Default exit code for clean shutdown
        while self.keep_looping:
            time_delay = self.__model.time_delay
            fade_time = self.__model.fade_time
            tm = time.time()
            pics = None
            loop_running = True # Assume loop is running
            skip_image = False
            if not self.paused and tm > self.__next_tm or self.__force_navigate:
                if self.__next_tm != 0:
                    self.__model.delete_file()

                pics = self.__model.get_next_file()

                if pics and pics[0] is not None:
                    is_video = os.path.splitext(pics[0].fname)[1].lower() in VIDEO_EXTENSIONS
                    
                    if is_video:
                        if self.__model.get_model_config()['video_playback_mode'] == 'ffmpeg':
                            self.__logger.info("Next item is a video. Playing as slideshow.")
                            self.__video_extractor.extract(pics[0].fname)
                            conf = self.__model.get_model_config()
                            self.__viewer.play_video_slideshow(pics[0], self.__video_extractor, 
                                                               conf['video_slideshow_fade_time'], 
                                                               conf['video_slideshow_time_delay'])
                            self.__model.save_current_file_state(pics[0].fname)
                            self.__next_tm = tm # Reset timer to continue immediately
                        else:
                            self.__logger.info("Next item is a video. Handing off to video player.")
                            self.__logger.info(f"Playing video: {pics[0].fname}")
                            
                            self.__model.save_resume_state() # Save state for file AFTER this video
                            # Play video. The viewer is now responsible for cleaning up the console *after* playback.
                            self.__viewer.play_video(pics[0].fname) 
                            exit_code = 10 # Special exit code to signal restart
                            self.keep_looping = False
                            break # Exit loop to allow service restart
                    else:
                        self.__force_navigate = False
                        self.__model.save_current_file_state(pics[0].fname) # Always save current image state
                        # It's an image, set the timer for the next change
                        orientation = "portrait" if pics[0].is_portrait else "landscape"
                        fname = os.path.basename(pics[0].fname)
                        if self.__model.get_viewer_config()['kenburns']:
                            self.__logger.info(f"Next item is a {orientation} image {fname}. Displaying. Using Ken Burns for {self.__model.time_delay} sec.")
                        else:
                            self.__logger.info(f"Next item is a {orientation} image {fname}. Displaying for {self.__model.time_delay} sec.")
                        # Timer will be reset after slideshow_is_running returns to account for loading time
                        # self.__next_tm = tm + self.__model.time_delay 
                        # MQTT logic for images
                        image_attr = {}
                        for key in self.__model.get_model_config()['image_attr']:
                            if key == 'PICFRAME GPS':
                                image_attr['latitude'] = pics[0].latitude
                                image_attr['longitude'] = pics[0].longitude
                            elif key == 'PICFRAME LOCATION':
                                image_attr['location'] = pics[0].location
                            else:
                                field_name = self.__model.EXIF_TO_FIELD[key]
                                image_attr[key] = pics[0].__dict__[field_name]
                        if self.__mqtt_config['use_mqtt']:
                            self.publish_state(pics[0].fname, image_attr)
                else:
                    # No valid file found, try again soon
                    self.__next_tm = 0
                    pics = None
            
            (loop_running, skip_image, _) = self.__viewer.slideshow_is_running( # This single call handles both new images and animation
                pics, time_delay, fade_time, self.__paused)

            if pics and not skip_image:
                # Reset timer after image has been loaded and displayed.
                # This ensures time_delay counts viewing time, excluding loading time.
                self.__next_tm = time.time() + self.__model.time_delay


            if not loop_running:
                self.__logger.info("Slideshow loop stopped (loop_running=False).")
                print("DEBUG: Slideshow loop stopped because viewer.slideshow_is_running returned False.")
                break
            if skip_image:
                self.__next_tm = 0
            
            self.__interface_peripherals.check_input()
        return exit_code

    def start(self):
        self.__viewer.slideshow_start() # Create the pi3d display first
        from picframe.interface_peripherals import InterfacePeripherals
        
        # Initialize VideoExtractor here, where we have access to the display dimensions
        mode = self.__model.get_model_config()['video_playback_mode']
        self.__logger.info(f"DEBUG: video_playback_mode is configured as: '{mode}'")
        print(f"DEBUG: video_playback_mode is configured as: '{mode}'")
        
        if mode == 'ffmpeg':
            try:
                # Ensure even dimensions for ffmpeg
                dw = self.__viewer.display_width if self.__viewer.display_width % 2 == 0 else self.__viewer.display_width - 1
                dh = self.__viewer.display_height if self.__viewer.display_height % 2 == 0 else self.__viewer.display_height - 1
                self.__video_extractor = VideoExtractor(
                    temp_dir=self.__model.get_model_config()['video_slideshow_temp_dir'],
                    step_time=self.__model.get_model_config()['video_slideshow_step_time'],
                    pillarbox_pct=self.__model.get_model_config()['video_slideshow_pillarbox_pct'],
                    resolution=(dw, dh),
                    quality=self.__model.get_model_config()['video_slideshow_quality']
                )
            except Exception as e:
                self.__logger.error(f"Failed to initialize VideoExtractor: {e}. Falling back to mpv.")
                self.__model.get_model_config()['video_playback_mode'] = 'mpv'

        self.__interface_peripherals = InterfacePeripherals(self.__model, self.__viewer, self)

        # ... (start mqtt and http server as before)

    def stop(self):
        self.keep_looping = False
        if self.__interface_peripherals:
            self.__interface_peripherals.stop()
        if self.__interface_mqtt:
            self.__interface_mqtt.stop()
        if self.__interface_http:
            self.__interface_http.stop()
        if self.__video_extractor:
            self.__video_extractor.stop()
        self.__model.stop_image_chache()
        self.__viewer.slideshow_stop()

    def __signal_handler(self, sig, frame):
        print('You pressed Ctrl-c!')
        self.keep_looping = False