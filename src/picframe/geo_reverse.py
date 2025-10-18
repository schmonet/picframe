import json
import urllib.request
import locale
import logging

URL = "https://nominatim.openstreetmap.org/reverse?format=geojson&lat={}&lon={}&zoom={}&email={}&accept-language={}"


class GeoReverse:
    def __init__(self, geo_key, zoom=18, key_list=None):
        self.__logger = logging.getLogger("geo_reverse.GeoReverse")
        self.__geo_key = geo_key
        self.__zoom = zoom
        self.__key_list = key_list
        self.__geo_locations = {}
        self.__language = locale.getlocale()[0][:2]

    def get_address(self, lat, lon):
        try:
            with urllib.request.urlopen(URL.format(lat, lon, self.__zoom, self.__geo_key, self.__language),
                                        timeout=3.0) as req:
                data = json.loads(req.read().decode())
            adr = data['features'][0]['properties']['address']
            # some experimentation might be needed to get a good set of alternatives in key_list
            adr_list = []
            if self.__key_list is not None:
                for part in self.__key_list:
                    for option in part:
                        if option in adr:
                            adr_list.append(adr[option])
                            break  # add just the first one from the options
            else:
                adr_list = adr.values()
            return ", ".join(adr_list)
        except urllib.error.URLError as e:
            self.__logger.error("Network error when trying to reverse geocode lat=%f, lon=%f: %s", lat, lon, e)
            return ""
        except Exception as e:
            self.__logger.error("An unexpected error occurred when trying to reverse geocode lat=%f, lon=%f: %s", lat, lon, e)
            return ""
