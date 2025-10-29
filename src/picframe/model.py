import yaml
import os
import time
import logging
import locale
import random
from picframe import geo_reverse, image_cache

DEFAULT_CONFIGFILE = "~/picframe_data/config/configuration.yaml"
DEFAULT_CONFIG = {
    'viewer': {
        'blur_amount': 12,
        'blur_zoom': 1.0,
        'blur_edges': False,
        'edge_alpha': 0.5,
        'fps': 20.0,
        'background': [0.0, 0.0, 0.0, 0.0],
        'solid_background': [0.2, 0.2, 0.3, 1.0],
        'blend_type': "blend",  # {"blend":0.0, "burn":1.0, "bump":2.0}
        'font_file': '~/picframe_data/data/fonts/NotoSans-Regular.ttf',
        'shader': '~/picframe_data/data/shaders/blend_new',
        'show_text_fm': '%b %d, %Y',
        'show_text_tm': 20.0,
        'show_text_sz': 40,
        'show_text': "name location",
        'text_justify': 'L',
        'text_bkg_hgt': 0.25,
        'text_opacity': 1.0,
        'fit': False,
        'video_fit_display': True,
        'kenburns': False,
        'display_x': 0,
        'display_y': 0,
        'display_w': None,
        'display_h': None,
        'display_power': 2,
        'use_glx': False,                          # default=False. Set to True on linux with xserver running
        'use_sdl2': True,
        'test_key': 'test_value',
        'mat_images': True,
        'mat_type': None,
        'outer_mat_color': None,
        'inner_mat_color': None,
        'outer_mat_border': 75,
        'inner_mat_border': 40,
        'inner_mat_use_texture': False,
        'outer_mat_use_texture': True,
        'mat_resource_folder': '~/picframe_data/data/mat',
        'show_clock': False,
        'clock_justify': "R",
        'clock_text_sz': 120,
        'clock_format': "%I:%M",
        'clock_opacity': 1.0,
        'clock_top_bottom': "T",
        'clock_wdt_offset_pct': 3.0,
        'clock_hgt_offset_pct': 3.0,
        'menu_text_sz': 40,
        'menu_autohide_tm': 10.0,
        'geo_suppress_list': [],
    },
    'model': {

        'pic_dir': '~/picframe_cache',
        'no_files_img': '~/picframe_data/data/no_pictures.jpg',
        'follow_links': False,
        'subdirectory': '',
        'recent_n': 3,
        'reshuffle_num': 1,
        'time_delay': 200.0,
        'fade_time': 10.0,
        'shuffle': True,
        'sort_cols': 'fname ASC',
        'image_attr': ['PICFRAME GPS'],  # image attributes send by MQTT, Keys are taken from exifread library, 'PICFRAME GPS' is special to retrieve GPS lon/lat # noqa: E501
        'load_geoloc': True,
        'locale': 'en_US.utf8',
        'key_list': [['tourism', 'amenity', 'isolated_dwelling'],
                     ['suburb', 'village'],
                     ['city', 'county'],
                     ['region', 'state', 'province'],
                     ['country']],
        'geo_key': 'this_needs_to@be_changed',  # use your email address
        'db_file': '~/picframe_data/data/pictureframe.db3',
        'portrait_pairs': False,
        'deleted_pictures': '~/DeletedPictures',
        'update_interval': 2.0,
        'log_level': 'WARNING',
        'log_file': '',
        'location_filter': '',
        'tags_filter': '',
        'delete_after_show': False,
        'group_by_dir': False, # New option
        'ffprobe_path': None,
    },
    'mqtt': {
        'use_mqtt': False,  # Set tue true, to enable mqtt
        'server': '',
        'port': 8883,
        'login': '',
        'password': '',
        'tls': '',
        'device_id': 'picframe',  # unique id of device. change if there is more than one picture frame
        'device_url': '',
    },
    'http': {
        'use_http': False,
        'path': '~/picframe_data/html',
        'port': 9000,
        'use_ssl': False,
        'keyfile': "/path/to/key.pem",
        'certfile': "/path/to/fullchain.pem"
    },
    'peripherals': {
        'input_type': None,  # valid options: {None, "keyboard", "touch", "mouse"}
        'buttons': {
            'pause': {'enable': True, 'label': 'Pause', 'shortcut': ' '},
            'display_off': {'enable': True, 'label': 'Display off', 'shortcut': 'o'},
            'location': {'enable': False, 'label': 'Location', 'shortcut': 'l'},
            'exit': {'enable': False, 'label': 'Exit', 'shortcut': 'e'},
            'power_down': {'enable': False, 'label': 'Power down', 'shortcut': 'p'}
        },
    },
}


class Pic:  # TODO could this be done more elegantly with namedtuple

    def __init__(self, fname, last_modified, file_id, orientation=1, exif_datetime=0,
                 f_number=0, exposure_time=None, iso=0, focal_length=None,
                 make=None, model=None, lens=None, rating=None, latitude=None,
                 longitude=None, width=0, height=0, is_portrait=0, location=None, title=None,
                 caption=None, tags=None):
        self.fname = fname
        self.last_modified = last_modified
        self.file_id = file_id
        self.orientation = orientation
        self.exif_datetime = exif_datetime
        self.f_number = f_number
        self.exposure_time = exposure_time
        self.iso = iso
        self.focal_length = focal_length
        self.make = make
        self.model = model
        self.lens = lens
        self.rating = rating
        self.latitude = latitude
        self.longitude = longitude
        self.width = width
        self.height = height
        self.is_portrait = is_portrait
        self.location = location
        self.tags = tags
        self.caption = caption
        self.title = title


class Model:

    def __init__(self, configfile=DEFAULT_CONFIGFILE):
        self.__logger = logging.getLogger("model.Model")
        self.__logger.debug('creating an instance of Model')
        self.__config = DEFAULT_CONFIG
        self.__last_file_change = 0.0
        configfile = os.path.expanduser(configfile)
        self.__logger.info("Open config file: %s:", configfile)
        with open(configfile, 'r') as stream:
            try:
                conf = yaml.safe_load(stream)
                for section in ['viewer', 'model', 'mqtt', 'http', 'peripherals']:
                    self.__config[section] = {**DEFAULT_CONFIG[section], **conf.get(section, {})
}

                self.__logger.debug('config data = %s', self.__config)
            except yaml.YAMLError as exc:
                self.__logger.error("Can't parse yaml config file: %s: %s", configfile, exc)
        root_logger = logging.getLogger()
        level = getattr(logging, self.get_model_config()['log_level'].upper(), logging.WARNING)
        root_logger.setLevel(level)
        log_file = self.get_model_config()['log_file']
        if log_file != '':
            filehandler = logging.FileHandler(log_file)  # NB default appending so needs monitoring
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            filehandler.setFormatter(formatter)
            for hdlr in root_logger.handlers[:]:  # remove the existing file handlers
                if isinstance(hdlr, logging.FileHandler):
                    root_logger.removeHandler(hdlr)
            root_logger.addHandler(filehandler)      # set the new handler

        self.__file_list = []  # this is now a list of tuples i.e (file_id1,) or (file_id1, file_id2)
        self.__number_of_files = 0  # this is shortcut for len(__file_list)
        self.__reload_files = True
        self.__file_index = 0  # pointer to next position in __file_list
        self.__current_pics = (None, None)  # this hold a tuple of (pic, None) or two pic objects if portrait pairs
        self.__num_run_through = 0

        model_config = self.get_model_config()  # alias for brevity as used several times below
        try:
            locale.setlocale(locale.LC_TIME, model_config['locale'])
        except Exception:
            self.__logger.error("error trying to set locale to {}".format(model_config['locale']))
        self.__pic_dir = os.path.expanduser(model_config['pic_dir'])
        self.__subdirectory = os.path.expanduser(model_config['subdirectory'])
        self.__load_geoloc = model_config['load_geoloc']
        self.__geo_reverse = geo_reverse.GeoReverse(model_config['geo_key'],
                                                    key_list=self.get_model_config()['key_list'])
        self.__image_cache = image_cache.ImageCache(self.__pic_dir,
                                                    model_config['follow_links'],
                                                    os.path.expanduser(model_config['db_file']),
                                                    self.__geo_reverse,
                                                    model_config['update_interval'],
                                                    model_config['portrait_pairs'],
                                                    model_config['ffprobe_path'])
        self.__deleted_pictures = model_config['deleted_pictures']
        self.__no_files_img = os.path.expanduser(model_config['no_files_img'])
        self.__sort_cols = model_config['sort_cols']
        self.__col_names = None
        # init where clauses through setters
        self.__where_clauses = {}
        self.location_filter = model_config['location_filter']
        self.tags_filter = model_config['tags_filter']

        self.__shown_albums_log_path = os.path.expanduser("~/shown_albums.log")
        self.__shown_albums = self.__read_shown_albums_log()
        self.__current_album_path = None

    def get_viewer_config(self):
        return self.__config['viewer']

    def get_model_config(self):
        return self.__config['model']

    def get_mqtt_config(self):
        return self.__config['mqtt']

    def get_http_config(self):
        if 'auth' in self.__config['http'] and self.__config['http']['auth'] and self.__config['http']['password'] is None:
            http_parent = os.path.abspath(os.path.join(self.__config['http']['path'], os.pardir))
            password_path = os.path.join(http_parent, 'basic_auth.txt')
            if not os.path.exists(password_path):
                new_password = self.__generate_random_string(64)
                with open(password_path, "w") as f:
                    f.write(new_password)
            with open(password_path, "r") as f:
                password = f.read()
                self.__config['http']['password'] = password
        return self.__config['http']

    def get_peripherals_config(self):
        return self.__config['peripherals']

    @property
    def fade_time(self):
        return self.__config['model']['fade_time']

    @fade_time.setter
    def fade_time(self, time):
        self.__config['model']['fade_time'] = time

    @property
    def time_delay(self):
        return self.__config['model']['time_delay']

    @time_delay.setter
    def time_delay(self, time):
        self.__config['model']['time_delay'] = time

    @property
    def subdirectory(self):
        return self.__subdirectory

    @subdirectory.setter
    def subdirectory(self, dir):
        _, root = os.path.split(self.__pic_dir)
        actual_dir = root
        if self.subdirectory != '':
            actual_dir = self.subdirectory
        if actual_dir != dir:
            if root == dir:
                self.__subdirectory = ''
            else:
                self.__subdirectory = dir
            self.__logger.info("Set subdirectory to: %s", self.__subdirectory)
            self.__reload_files = True

    @property
    def EXIF_TO_FIELD(self):  # bit convoluted TODO hold in config? not really configurable
        return self.__image_cache.EXIF_TO_FIELD

    @property
    def update_interval(self):
        return self.__config['model']['update_interval']

    @property
    def shuffle(self):
        return self.__config['model']['shuffle']

    @shuffle.setter
    def shuffle(self, val: bool):
        self.__config['model']['shuffle'] = val  # TODO should this be altered in config?
        self.__reload_files = True

    @property
    def location_filter(self):
        return self.__config['model']['location_filter']

    @location_filter.setter
    def location_filter(self, val):
        self.__config['model']['location_filter'] = val
        if len(val) > 0:
            self.set_where_clause("location_filter", self.__build_filter(val, "location"))
        else:
            self.set_where_clause("location_filter")  # remove from where_clause
        self.__reload_files = True

    @property
    def tags_filter(self):
        return self.__config['model']['tags_filter']

    @tags_filter.setter
    def tags_filter(self, val):
        self.__config['model']['tags_filter'] = val
        if len(val) > 0:
            self.set_where_clause("tags_filter", self.__build_filter(val, "tags"))
        else:
            self.set_where_clause("tags_filter")  # remove from where_clause
        self.__reload_files = True

    def __build_filter(self, val, field):
        if val.count("(") != val.count(")"):
            return None  # this should clear the filter and not raise an error
        val = val.replace(";", "").replace("'", "").replace("%", "").replace('"', '')  # SQL scrambling
        tokens = ("(", ")", "AND", "OR", "NOT")  # now copes with NOT
        val_split = val.replace("(", " ( ").replace(")", " ) ").split()  # so brackets not joined to words
        filter = []
        last_token = ""
        for s in val_split:
            s_upper = s.upper()
            if s_upper in tokens:
                if s_upper in ("AND", "OR"):
                    if last_token in ("AND", "OR"):
                        return None  # must have a non-token between
                    last_token = s_upper
                filter.append(s)
            else:
                if last_token is not None:
                    filter.append("{} LIKE '%{}%'".format(field, s))
                else:
                    filter[-1] = filter[-1].replace("%'", " {}%'".format(s))
                last_token = None
        return "({})".format(" ".join(filter))  # if OR outside brackets will modify the logic of rest of where clauses

    def set_where_clause(self, key, value=None):
        # value must be a string for later join()
        if (value is None or len(value) == 0):
            if key in self.__where_clauses:
                self.__where_clauses.pop(key)
            return
        self.__where_clauses[key] = value

    def pause_looping(self, val):
        self.__image_cache.pause_looping(val)

    def stop_image_chache(self):
        self.__image_cache.stop()

    def purge_files(self):
        self.__image_cache.purge_files()

    def get_directory_list(self):
        _, root = os.path.split(self.__pic_dir)
        actual_dir = root
        if self.subdirectory != '':
            actual_dir = self.subdirectory
        follow_links = self.get_model_config()['follow_links']
        subdir_list = next(os.walk(self.__pic_dir, followlinks=follow_links))[1]
        subdir_list[:] = [d for d in subdir_list if not d[0] == '.']
        if not follow_links:
            subdir_list[:] = [d for d in subdir_list if not os.path.islink(self.__pic_dir + '/' + d)]
        subdir_list.insert(0, root)
        return actual_dir, subdir_list

    def force_reload(self):
        self.__reload_files = True

    def set_next_file_to_previous_file(self):
        self.__file_index = (self.__file_index - 2) % self.__number_of_files  # TODO deleting last image results in ZeroDivisionError # noqa: E501

    def get_next_file(self):
        missing_images = 0

        # loop until we acquire a valid image set
        while True:
            pic1 = None
            pic2 = None

            # Reload the playlist if requested
            if self.__reload_files:
                # When reloading, the file list might be empty if a new album was just copied
                # by the watcher but the image_cache hasn't finished processing it yet.
                # We retry for a few seconds to give the cache time to catch up.
                max_wait_time = 10 # seconds
                start_time = time.time()
                self.__logger.info("Reloading file list...")
                while time.time() - start_time < max_wait_time:
                    self.__get_files() # This queries the DB
                    missing_images = 0
                    if self.__number_of_files > 0:
                        self.__logger.info("Reload successful, found %d files.", self.__number_of_files)
                        break
                    self.__logger.info("Reload attempt found no files. Retrying...")
                    time.sleep(1) # Wait 1 second before retrying
                else: # This 'else' belongs to the 'while' loop, executed if the loop finishes without break
                    self.__logger.warning("Failed to reload file list after %d seconds. No files found.", max_wait_time)

            # If we don't have any files to show, prepare the "no images" image
            # Also, set the reload_files flag so we'll check for new files on the next pass...
            if self.__number_of_files == 0 or missing_images >= self.__number_of_files:
                pic1 = Pic(self.__no_files_img, 0, 0)
                self.__reload_files = True
                break

            # If we've displayed all images...
            #   If it's time to shuffle, set a flag to do so
            #   Loop back, which will reload and shuffle if necessary
            if self.__file_index == self.__number_of_files:
                self.__num_run_through += 1
                if self.shuffle and self.__num_run_through >= self.get_model_config()['reshuffle_num']:
                    self.__reload_files = True
                self.__file_index = 0
                continue

            # Load the current image set
            file_ids = self.__file_list[self.__file_index]
            pic_row = self.__image_cache.get_file_info(file_ids[0])
            pic1 = Pic(**pic_row) if pic_row is not None else None
            if len(file_ids) == 2:
                pic_row = self.__image_cache.get_file_info(file_ids[1])
                pic2 = Pic(**pic_row) if pic_row is not None else None

            # Verify the images in the selected image set actually exist on disk
            # Blank out missing references and swap positions if necessary to try and get
            # a valid image in the first slot.
            if pic1 and not os.path.isfile(pic1.fname):
                pic1 = None
            if pic2 and not os.path.isfile(pic2.fname):
                pic2 = None
            if (not pic1 and pic2):
                pic1, pic2 = pic2, pic1

            # Increment the image index for next time
            self.__file_index += 1

            # If pic1 is valid here, everything is OK. Break out of the loop and return the set
            if pic1:
                break

            # Here, pic1 is undefined. That's a problem. Loop back and get another image set.
            # Track the number of times we've looped back so we can abort if we don't have *any* images to display
            missing_images += 1

        self.__current_pics = (pic1, pic2)
        return self.__current_pics

    def get_number_of_files(self):
        return sum(
                    sum(1 for pic in pics if pic is not None)
                    for pics in self.__file_list
                )

    def get_current_pics(self):
        return self.__current_pics

    def delete_file(self):
        # This method is now called by the controller after a picture has been shown.
        # It deletes the file(s) for the *current* slide.
        if not self.get_model_config().get('delete_after_show', False):
            return # Feature is disabled in config

        for pic in self.__current_pics:
            if pic is None or self.__no_files_img in pic.fname:
                continue

            f_to_delete = pic.fname

            try:
                if os.path.exists(f_to_delete):
                    os.remove(f_to_delete)
                    self.__logger.info("Permanently deleted file: %s", f_to_delete)
                    # Immediately remove from image_cache database
                    self.__image_cache.delete_file_from_db(pic.file_id)
                else:
                    self.__logger.warning("File not found for deletion: %s", f_to_delete)
            except OSError as e:
                self.__logger.error("Could not permanently delete file '%s': %s", f_to_delete, e)
        
        # After deletion, force a reload of the file list to ensure deleted files are not shown again.
        # This also implicitly handles the removal from the internal __file_list.
        self.force_reload()

    def __get_files(self):
        if self.subdirectory != "":
            picture_dir = os.path.join(self.__pic_dir, self.subdirectory)  # TODO catch, if subdirecotry does not exist
        else:
            picture_dir = self.__pic_dir

        model_config = self.get_model_config()
        group_by_dir = model_config['group_by_dir']
        shuffle_global = model_config['shuffle'] # This is the global shuffle setting

        if group_by_dir:
            # Check if the current album is finished. An album is finished if the file list is empty.
            # Because delete_after_show forces a reload, we must re-query the db to get the current state.
            if self.__current_album_path:
                where_clause_check = " AND ".join([f"fname LIKE '{self.__current_album_path}/%'"] + list(self.__where_clauses.values()))
                if not self.__image_cache.query_cache(where_clause_check, "1"):
                    self.__logger.info(f"Album '{self.__current_album_path}' is now empty. Selecting a new one.")
                    self.__current_album_path = None  # Mark as finished

            # If no album is selected (or the previous one finished), find and select a new one.
            if not self.__current_album_path:
                # Correctly identify albums at depth 2 ({YYYY}/{Ort})
                all_albums = []
                if os.path.isdir(picture_dir):
                    for year_dir in os.listdir(picture_dir):
                        year_path = os.path.join(picture_dir, year_dir)
                        if os.path.isdir(year_path):
                            for loc_dir in os.listdir(year_path):
                                loc_path = os.path.join(year_path, loc_dir)
                                if os.path.isdir(loc_path):
                                    all_albums.append(loc_path)
                
                unshown_albums = [album for album in all_albums if album not in self.__shown_albums]

                if not unshown_albums and all_albums:
                    self.__logger.info("All albums shown. Resetting shown_albums.log.")
                    self.__shown_albums.clear()
                    self.__write_shown_albums_log()
                    unshown_albums = all_albums

                if unshown_albums:
                    self.__current_album_path = random.choice(unshown_albums)
                    self.__logger.info(f"Selected album for playback: {self.__current_album_path}")
                    self.__shown_albums.add(self.__current_album_path)
                    self.__write_shown_albums_log()
                else:
                    self.__logger.warning("No unshown albums found.")
                    self.__file_list = [] # No albums available
                    self.__number_of_files = 0
                    self.__file_index = 0
                    self.__reload_files = False
                    return

            # Now, get the sorted file list for the currently selected album.
            if self.__current_album_path:
                where_list = [f"fname LIKE '{self.__current_album_path}/%'"]
                where_list.extend(self.__where_clauses.values())
                where_clause = " AND ".join(where_list)

                sort_list = []
                if shuffle_global:
                    sort_list.append("RANDOM()")
                else:
                    if self.__col_names is None:
                        self.__col_names = self.__image_cache.get_column_names()
                    for col in self.__sort_cols.split(","):
                        colsplit = col.split()
                        if colsplit[0] in self.__col_names and (len(colsplit) == 1 or colsplit[1].upper() in ("ASC", "DESC")):
                            sort_list.append(col)
                    sort_list.append("fname ASC")
                sort_clause = ",".join(sort_list)

                self.__file_list = self.__image_cache.query_cache(where_clause, sort_clause)
            else:
                self.__file_list = [] # Should not happen if albums were found
        else:
            # Existing logic for non-grouped display (flat list from pic_dir)
            where_list = [f"fname LIKE '{picture_dir}/%'"]
            where_list.extend(self.__where_clauses.values())
            where_clause = " AND ".join(where_list) if len(where_list) > 0 else "1"

            sort_list = []
            recent_n = model_config["recent_n"]
            if recent_n > 0:
                sort_list.append(f"last_modified < {time.time() - 3600 * 24 * recent_n:.0f}")

            if shuffle_global:
                sort_list.append("RANDOM()")
            else:
                if self.__col_names is None:
                    self.__col_names = self.__image_cache.get_column_names()
                for col in self.__sort_cols.split(","):
                    colsplit = col.split()
                    if colsplit[0] in self.__col_names and (len(colsplit) == 1 or colsplit[1].upper() in ("ASC", "DESC")):
                        sort_list.append(col)
                sort_list.append("fname ASC")
            sort_clause = ",".join(sort_list)

            self.__file_list = self.__image_cache.query_cache(where_clause, sort_clause)

        self.__number_of_files = len(self.__file_list)
        self.__file_index = 0
        self.__num_run_through = 0
        self.__reload_files = False

    def __generate_random_string(self, length):
        random_bytes = os.urandom(length // 2)
        random_string = ''.join('{:02x}'.format(ord(chr(byte))) for byte in random_bytes)
        return random_string

    def __read_shown_albums_log(self):
        log_file = os.path.expanduser(self.__shown_albums_log_path)
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def __write_shown_albums_log(self):
        log_file = os.path.expanduser(self.__shown_albums_log_path)
        with open(log_file, 'w') as f:
            for album in self.__shown_albums:
                f.write(f"{album}\n")