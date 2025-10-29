"""Controller of picframe."""

import logging
import time
import signal
import sys
import ssl
import os
from picframe.video_streamer import VIDEO_EXTENSIONS


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
        while self.keep_looping:
            time_delay = self.__model.time_delay
            fade_time = self.__model.fade_time
            tm = time.time()
            pics = None

            if not self.paused and tm > self.__next_tm or self.__force_navigate:
                if self.__next_tm != 0:
                    self.__model.delete_file()

                self.__force_navigate = False
                pics = self.__model.get_next_file()

                if pics and pics[0] is not None:
                    is_video = os.path.splitext(pics[0].fname)[1].lower() in VIDEO_EXTENSIONS
                    
                    if is_video:
                        self.__logger.info("Next item is a video. Handing off to video player.")
                        self.__viewer.play_video_blocking(pics[0].fname)
                        self.__next_tm = 0  # Trigger next file immediately after video
                        pics = None  # Clear pics so slideshow_is_running knows not to load a new image
                    else:
                        # It's an image, set the timer for the next change
                        self.__logger.info("Next item is an image. Displaying.")
                        self.__next_tm = tm + self.__model.time_delay
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

            # This call now handles image display and re-initialization after a video
            (loop_running, skip_image, _) = self.__viewer.slideshow_is_running(
                pics, time_delay, fade_time, self.__paused)
            
            if not loop_running:
                break
            if skip_image:
                self.__next_tm = 0
            
            self.__interface_peripherals.check_input()

    def start(self):
        # Don't start the display here. The loop will handle it.
        from picframe.interface_peripherals import InterfacePeripherals
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
        self.__model.stop_image_chache()
        self.__viewer.slideshow_stop()

    def __signal_handler(self, sig, frame):
        print('You pressed Ctrl-c!')
        self.keep_looping = False