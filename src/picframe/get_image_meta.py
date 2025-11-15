import exifread
import os
import logging
import time
import subprocess
import json
from PIL import Image
from datetime import datetime

class GetImageMeta:
    """
    A class for extracting metadata from image files.
    """

    def __init__(self, filename):
        self.__logger = logging.getLogger("get_image_meta.GetImageMeta")
        self.__filename = filename
        self.__tags = {}
        try:
            with open(self.__filename, 'rb') as f:
                self.__tags = exifread.process_file(f, details=False)
            self.__logger.debug(self.__tags)
        except Exception as e:
            self.__logger.warning("Error reading EXIF data from %s: %s", self.__filename, e)

        try:
            self.__image = self.get_image_object(self.__filename)
            if self.__image:
                self.width, self.height = self.__image.size
            else:
                self.width, self.height = 0, 0
        except Exception as e:
            self.__logger.warning("Could not get image properties for %s: %s", self.__filename, e)
            self.width, self.height = 0, 0

    @staticmethod
    def get_image_object(filename):
        try:
            image = Image.open(filename)
            # Some HEIC files are not correctly read by Pillow without loading them.
            if image.format.upper() in ['HEIF', 'HEIC']:
                image.load()
            return image
        except Exception as e:
            logging.getLogger("get_image_meta.GetImageMeta").warning("Could not open image %s: %s", filename, e)
            return None

    @property
    def size(self):
        return (self.width, self.height)

    def get_exif(self, key):
        if key in self.__tags:
            if key == 'EXIF DateTimeOriginal':
                return self.__tags[key].values
            elif key == 'IPTC Keywords':
                values = self.__tags[key].values
                return ", ".join([v.decode('utf-8') for v in values]) if isinstance(values, list) else values.decode('utf-8')
            else:
                return self.__tags[key].printable
        return None

    def get_orientation(self):
        orientation = 1
        try:
            if 'Image Orientation' in self.__tags:
                orientation = self.__tags['Image Orientation'].values[0]
        except Exception as e:
            self.__logger.warning("Could not get orientation for %s: %s", self.__filename, e)
        return orientation

    def get_location(self):
        def convert_to_degress(value):
            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)

        lat = None
        lon = None
        try:
            if "GPS GPSLatitude" in self.__tags and "GPS GPSLatitudeRef" in self.__tags and \
               "GPS GPSLongitude" in self.__tags and "GPS GPSLongitudeRef" in self.__tags:
                lat_ref = self.__tags["GPS GPSLatitudeRef"].printable
                lat = convert_to_degress(self.__tags["GPS GPSLatitude"])
                if lat_ref != "N":
                    lat = 0 - lat

                lon_ref = self.__tags["GPS GPSLongitudeRef"].printable
                lon = convert_to_degress(self.__tags["GPS GPSLongitude"])
                if lon_ref != "E":
                    lon = 0 - lon
        except Exception as e:
            self.__logger.warning("Could not get location for %s: %s", self.__filename, e)

        return {'latitude': lat, 'longitude': lon}


def get_video_info(file_path_name, ffprobe_path=None):
    """
    Extracts metadata from a video file using ffprobe.
    """
    logger = logging.getLogger("get_image_meta.get_video_info")
    ffprobe_cmd = ffprobe_path if ffprobe_path else 'ffprobe'
    command = [
        ffprobe_cmd,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path_name
    ]
    meta = {}
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        info = json.loads(result.stdout)

        video_stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            logger.warning("No video stream found in %s", file_path_name)
            return meta

        meta['width'] = int(video_stream.get('width', 0))
        meta['height'] = int(video_stream.get('height', 0))
        meta['orientation'] = 1 # Default for video

        # Check for rotation tag
        if 'tags' in video_stream and 'rotate' in video_stream['tags']:
            rotation = int(video_stream['tags']['rotate'])
            if rotation == 90 or rotation == 270:
                meta['width'], meta['height'] = meta['height'], meta['width']

        # Get creation time from format tags if available
        creation_time_str = info.get('format', {}).get('tags', {}).get('creation_time')
        if creation_time_str:
            try:
                # Handle timezone info like '2023-01-01T12:00:00.000000Z'
                dt_object = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
                meta['exif_datetime'] = dt_object.timestamp()
            except ValueError:
                logger.warning("Could not parse creation_time '%s'", creation_time_str)
                meta['exif_datetime'] = os.path.getmtime(file_path_name)
        else:
            meta['exif_datetime'] = os.path.getmtime(file_path_name)

    except FileNotFoundError:
        logger.error("ffprobe command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        logger.error("ffprobe failed for %s: %s", file_path_name, e.stderr)
    except Exception as e:
        logger.error("An error occurred while getting video info for %s: %s", file_path_name, e)

    return meta
