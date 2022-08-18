'''
This class allows you to make one of two possible calls to OpenWeather’s
API. For more information, see https://openweathermap.org/api/one-call-api
Access to the API is controlled by key.

Register for developer access here: https://openweathermap.org/appid

NOTE this class does not parse the incoming data, which is highly complex.
    It is up to your application to extract the data you require.

Version:        2.0.2
Author:         Tony Smith (@smittytone)
License:        MIT
Copyright:      2022
'''

class OpenWeather:
    '''
    See above
    '''

    # *********** CONSTANTS **********

    VERSION = "2.0.1"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/onecall"


    # *********Private Properties **********

    requests = None
    apikey = None
    units = "metric"
    lang = "en"
    excludes = None
    debug = False


    # *********** CONSTRUCTOR **********

    def __init__(self, requests_object=None, api_key=None, do_debug=False):
        '''
        Instantiate the class.

        Args:
            requests_object [requests] An instance of the Requests class.
            api_key [string]           Your OpenWeather API key.
            do_debug [bool             Output debug information. Default: False.
        '''

        assert api_key is not None and api_key != "", \
            "[ERROR] OpenWeather() requires an API key"
        assert requests_object is not None, \
            "[ERROR] OpenWeather() requires a valid requests instance"

        # Set private properties
        self.debug = do_debug
        self.apikey = api_key
        self.requests = requests_object


    # *********** PUBLIC METHODS **********

    def request_forecast(self, latitude=999.0, longitude=999.0):
        '''
        Make a request for future weather data.

        Args:
            longitude [float]   Longitude of location for which a forecast is required.
            latitude [float]    Latitude of location for which a forecast is required.

        Returns:
            The weather data.
        '''

        # Check the supplied co-ordinates
        if not self._check_coords(longitude, latitude, "request_forecast"):
            return {"error": "Co-ordinate error"}

        # Co-ordinates good, so get a forecast
        url = self.FORECAST_URL
        url += f"lat={latitude:.6f}&lon={longitude:.6f}&appid={self.apikey}"
        url = self._add_options(url)
        self._print_debug("Request URL: " + url)
        return self._send_request(url)


    def set_unit(self, requested_units="standard"):
        '''
        Specify the preferred weather report's units.

        Args:
            units [string]  Country code indicating the type of units.
                            Default: automatic, based on location.

        Returns:
            The instance (self)
        '''

        unit_types = ["metric", "imperal", "standard"]
        requested_units = requested_units.lower()
        if requested_units not in unit_types:
            err = "OpenWeather.set_units() incorrect units option selected ("
            err += requested_units + "); using default value (standard)"
            self._print_error(err)
            requested_units = "standard"

        self.units = requested_units
        self._print_debug("OpenWeather units set: " + self.units)
        return self


    def set_language(self, language="en"):
        '''
        Specify the preferred weather report's language.

        Args:
            language [string]   Country code indicating the language.
                                Default: English.

        Returns:
            The instance (self)
        '''

        lang_types = ["af", "al", "ar", "az", "bg", "ca", "cz", "da", "de",
                      "el", "en", "eu", "fa", "fi", "fr", "gl", "he", "hi",
                      "hr", "hu", "id", "it", "ja", "kr", "la", "lt", "mk",
                      "no", "nl", "pl", "pt", "pt_br", "ro", "ru", "se", "sv",
                      "sk", "sl", "sp", "es", "sr", "th", "tr", "ua", "uk",
                      "vi", "zh_cn", "zh_tw", "zu"]
        language = language.lower()
        if language not in lang_types:
            err = "OpenWeather.set_language() incorrect language option selected ("
            err += language + "); using default value (en)"
            self._print_error(err)
            language = "en"

        self.lang = language
        self._print_debug("OpenWeather language set: " + self.lang)
        return self


    def exclude(self, exclude_list):
        '''
        Indicate items OpenWeather should not include in its response.

        Args:
            exclude_list [array]    List of items to exclude. Default: no exclusions.

        Returns:
            The instance (self)
        '''
        exclude_types = ["current", "minutely", "hourly", "daily", "alerts"]
        matches = []
        for item in exclude_list:
            for exclude_type in exclude_types:
                if item == exclude_type: matches.append(item)

        if not matches:
            self._print_error("OpenWeather.exclude() incorrect exclusions passed")
            return self

        self.excludes = ""
        for item in matches:
            self.excludes += (item + ",")

        if self.excludes:
            self.excludes = self.excludes[0: len(self.excludes) - 1]
        self._print_debug("OpenWeather excludes set: " + self.excludes)
        return self


    # *********PRIVATE FUNCTIONS - DO NOT CALL **********

    def _send_request(self, request_uri):
        '''
        Send a request to OpenWeather.

        Args:
            request_uri [string]    The URL-encoded request to send.

        Returns:
            Dictionary containing `data` or `err` keys.
        '''

        return self._process_response(self.requests.get(request_uri))


    def _process_response(self, response):
        '''
        Process a response received from OpenWeather.

        Args:
            response [response] The HTTPS response.

        Returns
            Dictionary containing `data` or `err` keys.
        '''

        err = ""
        data = ""

        if response.status_code != 200:
            err = "Unable to retrieve forecast data (code: " + str(response.status_code) + ")"
        else:
            try:
                # Have we valid JSON?
                data = response.json()
                data["statuscode"] = response.status_code
            except self.requests.exceptions.JSONDecodeError as exp:
                err = "Unable to decode data received from Open Weather: " + str(exp)

        response.close()

        if err:
            return {"err": err}

        self._print_debug("Received data:\n", data)
        return {"data": data}


    def _check_coords(self, longitude=999.0, latitude=999.0, caller="function"):
        '''
        Check that valid co-ordinates have been supplied.

        Args:
            longitude [float]   Longitude of location for which a forecast is required.
            latitude [float]    Latitude of location for which a forecast is required.
            caller [string]     The name of the calling function, for error reporting.

        Returns:
            Whether the supplied co-ordinates are valid (True) or not (False).
        '''

        err = "OpenWeather." + caller + "() "
        try:
            longitude = float(longitude)
        except (ValueError, OverflowError):
            self._print_error(err + "can't process supplied longitude value")
            return False

        try:
            latitude = float(latitude)
        except (ValueError, OverflowError):
            self._print_error(err + "can't process supplied latitude value")
            return False

        if longitude == 999.0 or latitude == 999.0:
            self._print_error(err + "requires valid latitude/longitude co-ordinates")
            return False

        if latitude > 90.0 or latitude < -90.0:
            self._print_error(err + "latitude co-ordinate out of range")
            return False

        if longitude > 180.0 or longitude < -180.0:
            self._print_error(err + "latitude co-ordinate out of range")
            return False
        return True


    def _add_options(self, baseurl=""):
        '''
        Add URL-encoded options to the request URL. Used when assembling HTTPS requests.

        Args:
            baseurl [string]    Optional base URL.

        Returns
            The full URL with added options.
        '''

        opts = "&units=" + self.units
        if self.lang: opts += "&lang=" + self.lang
        if self.excludes: opts += "&exclude=" + self.excludes
        return baseurl + opts

    def _print_error(self, msg):
        '''
        Print an error message.

        Args:
            msg [string]    The error message.
        '''

        print("[ERROR]", msg)


    def _print_debug(self, *msgs):
        '''
        Print a debug message.

        Args:
            msg [tuple]    One or more string components
        '''
        if self.debug:
            msg = ("[DEBUG]") + msgs
            print(msg)
