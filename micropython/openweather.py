import urequests as requests

class OpenWeather:
    """
    This class allows you to make one of two possible calls to OpenWeather’s
    API. For more information, see https://openweathermap.org/api/one-call-api
    Access to the API is controlled by key. Register for developer access
    here: https://openweathermap.org/appid

    NOTE this class does not parse the incoming data, which is highly complex.
         It is up to your application to extract the data you require.

    MicroPython version for Raspberry Pi Pico W

    Version:        2.0.0.m
    Author:         Tony Smith (@smittytone)
    License:        MIT
    Copyright:      2022
    """

    # *********** CONSTANTS **********

    VERSION = const("2.0.0.m")
    FORECAST_URL = const("https://api.openweathermap.org/data/2.5/onecall")

    # *********Private Properties **********
    apikey = None
    units = "metric"
    lang = "en"
    excludes = None
    debug = False

    # *********** CONSTRUCTOR **********

    def __init__(self, key=None, do_debug=False):
        assert key != None and key != "", "[ERROR] OpenWeather() requires an API key"

        # Set private properties
        self.debug = do_debug
        self.apikey = key


    # *********** PUBLIC METHODS **********

    def request_forecast(self, latitude=999.0, longitude=999.0):
        """
        Make a request for future weather data.

        Args:
            longitude [float]   Longitude of location for which a forecast is required.
            latitude [float]    Latitude of location for which a forecast is required.

        Returns:
            Dictionary containing `data` or `err` keys.
        """
        # Check the supplied co-ordinates
        if not self._check_coords(longitude, latitude, "request_forecast"):
            return {"error": "Co-ordinate error"}

        # Co-ordinates good, so get a forecast
        url = self.FORECAST_URL
        url += "?lat={:.6f}&lon={:.6f}&appid={}".format(latitude, longitude, self.apikey)
        url = self._add_options(url)
        if self.debug:
            print("[DEBUG] Request URL: " + url)
        return self._send_request(url)


    def set_unit(self, requested_units="standard"):
        """
        Specify the preferred weather report's units.

        Args:
            units [string]  Country code indicating the type of units.
                            Default: automatic, based on location.

        Returns:
            The instance (self)
        """
        unit_types = ["metric", "imperal", "standard"]
        requested_units = requested_units.lower()
        if not requested_units in unit_types:
            print("[ERROR] OpenWeather.set_units() incorrect units option selected (" + requested_units + "); using default value (standard)")
            requested_units = "standard"

        self.units = requested_units
        if self.debug:
            print("[DEBUG] OpenWeather units set: " + self.units)
        return self


    def set_language(self, language="en"):
        """
        Specify the preferred weather report's language.

        Args:
            language [string}   Country code indicating the language.
                                Default: English.

        Returns:
            The instance (self)
        """
        lang_types = ["af", "al", "ar", "az", "bg", "ca", "cz", "da", "de", "el", "en", "eu", "fa",
                    "fi", "fr", "gl", "he", "hi", "hr", "hu", "id", "it", "ja", "kr", "la", "lt",
                    "mk", "no", "nl", "pl", "pt", "pt_br", "ro", "ru", "se", "sv", "sk", "sl", "sp", "es", "sr", "th", "tr", "ua", "uk", "vi", "zh_cn", "zh_tw", "zu"]
        language = language.lower()
        if not language in lang_types:
            print("[ERROR] OpenWeather.set_language() incorrect language option selected (" + language + "); using default value (en)")
            language = "en"

            self.lang = language
            if self.debug:
                print("[DEBUG] OpenWeather language set: " + self.lang)
            return self

    def exclude(self, list=[]):
        exclude_types = ["current", "minutely", "hourly", "daily", "alerts"]
        matches = []
        for item in list:
            for exclude_type in exclude_types:
                if item == type: matches.append(item)

        if not matches:
            print("[ERROR] OpenWeather.exclude() incorrect exclusions passed")
            return self

        self.excludes = ""
        for item in matches:
            self.excludes += (item + ",")

        if self.excludes:
            self.excludes = self.excludes[0: len(self.excludes) - 1]
        if self.debug:
            print("[DEBUG] OpenWeather excludes set: " + self.excludes)
        return self

    # *********PRIVATE FUNCTIONS - DO NOT CALL **********

    def _send_request(self, request_uri):
        """
        Send a request to OpenWeather.

        Args:
            request_uri [string]    The URL-encoded request to send.

        Returns:
            Dictionary containing `data` or `err` keys.
        """
        return self._process_response(requests.get(request_uri))


    def _process_response(self, response):
        """
        Process a response received from OpenWeather.

        Args:
            response [response]     The HTTPS response.

        Returns
            Dictionary containing `data` or `err` keys.
        """
        err = ""
        data = ""

        if response.status_code != 200:
            err = "Unable to retrieve forecast data (code: " + str(response.status_code) + ")"
        else:
            try:
                # Have we valid JSON?
                data = response.json()
                data["statuscode"] = response.status_code
            except BaseException as exp:
                err = "Unable to decode data received from Open Weather: " + str(exp)

        # Close the response
        response.close()

        # Issue the response data
        if err:
            return {"err": err}
        else:
            if self.debug:
                print("[DEBUG] Received data:",data)
            return {"data": data}


    def _check_coords(self, longitude=999.0, latitude=999.0, caller="function"):
        """
        Check that valid co-ordinates have been supplied.

        Args:
            longitude [float]   Longitude of location for which a forecast is required.
            latitude [float]    Latitude of location for which a forecast is required.
            caller [string]     The name of the calling function, for error reporting.

        Returns:
            Whether the supplied co-ordinates are valid (True) or not (False).
        """
        try:
            longitude = float(longitude)
        except:
            print("[ERROR] OpenWeather." + caller + "() can't process supplied longitude value")
            return False

        try:
            latitude = float(latitude)
        except:
            print("[ERROR] OpenWeather." + caller + "() can't process supplied latitude value")
            return False

        if longitude == 999.0 or latitude == 999.0:
            print("[ERROR] OpenWeather." + caller + "() requires valid latitude/longitude co-ordinates")
            return False

        if latitude > 90.0 or latitude < -90.0:
            print("[ERROR] OpenWeather." + caller + "() requires valid a latitude co-ordinate (value out of range)")
            return False

        if longitude > 180.0 or longitude < -180.0:
            print("[ERROR] OpenWeather." + caller + "() requires valid a latitude co-ordinate (value out of range)")
            return False
        return True


    def _add_options(self, baseurl=""):
        """
        Add URL-encoded options to the request URL. Used when assembling HTTPS requests.

        Args:
            baseurl [string]    Optional base URL.

        Returns
            The full URL with added options.
        """
        opts = "&units=" + self.units
        if self.lang: opts += "&lang=" + self.lang
        if self.excludes: opts += "&exclude=" + self.excludes
        return baseurl + opts
