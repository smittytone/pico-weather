class OpenWeather:
    """
    This class allows you to make one of two possible calls to OpenWeather’s
    API. For more information, see https://openweathermap.org/api/one-call-api
    Access to the API is controlled by key. Register for developer access
    here: https://openweathermap.org/appid

    NOTE this class does not parse the incoming data, which is highly complex.
        It is up to your application to extract the data you require.

    Version:        1.0.0
    Author:         Tony Smith (@smittytone)
    License:        MIT
    Copyright:      2022
    """

    # *********** CONSTANTS **********

    VERSION = "1.0.0"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/onecall"

    # *********Private Properties **********
    requests = None
    apikey = None
    units = None
    lang = None
    excludes = None
    debug = False

    # *********** CONSTRUCTOR **********

    def __init__(self, requests_obj=None, key=None, do_debug=False) {
        assert key != None and key != "", "ERROR - OpenWeather() requires an API key"
        assert requests_obj != None, "ERROR - OpenWeather() requires a valid requests instance"

        # Set private properties
        debug = do_debug
        units = "standard"
        apikey = key
        requests = requests_obj


    # *********** PUBLIC METHODS **********

    def request_forecast(self, latitude=999.0, longitude=999.0):
        """
        Make a request for future weather data.

        @param {float}    longitude  - Longitude of location for which a forecast is required.
        @param {float}    latitude   - Latitude of location for which a forecast is required.
        @param {function} [callback] - Optional asynchronous operation callback.
        *
        @returns {table|string|null} If 'callback' is null, the function returns a table with key 'response';
                                    if there was an error, the function returns a table with key 'error'.
                                    If 'callback' is not null, the function returns nothing;
        """
        # Check the supplied co-ordinates
        if not _check_coords(longitude, latitude, "request_forecast")):
            return {"error": "Co-ordinate error"}

        # Co-ordinates good, so get a forecast
        url = FORECAST_URL
        utl += F"?lat={format("%.6f", latitude)}&lon={format("%.6f", longitude)} &appid={apikey}"
        url = _add_options(url)
        return _send_request(url)


    def set_unit(self, requested_units="standard"):
        """
        Specify the preferred weather report's units.

        Args:
            units (string):     Country code indicating the type of units.
                                Default: automatic, based on location.

        Returns:
            The instance (self)
        """
        unit_types = ["metric", "imperal", "standard"]
        requested_units = requested_units.lower()
        if not requested_units in unit_types:
            if debug:
                print("OpenWeather.set_units() incorrect units option selected (" + units + "); using default value (standard)")
            requested_units = "standard"

        units = requested_units
        return self


    def set_language(self, language="en"):
    """
    Specify the preferred weather report's language.

    Args:
        language (string):  Country code indicating the language.
                            Default: English.

    Returns:
        The instance (self)
    """
    lang_types = ["af", "al", "ar", "az", "bg", "ca", "cz", "da", "de", "el", "en", "eu", "fa",
                  "fi", "fr", "gl", "he", "hi", "hr", "hu", "id", "it", "ja", "kr", "la", "lt",
                  "mk", "no", "nl", "pl", "pt", "pt_br", "ro", "ru", "se", "sv", "sk", "sl", "sp", "es", "sr", "th", "tr", "ua", "uk", "vi", "zh_cn", "zh_tw", "zu"]
    language = language.lower()
    if not language in lang_types:
        if debug:
            print("OpenWeather.set_language() incorrect language option selected (" + language + "); using default value (en)")
            language = "en"

        lang = language
        return self


    function exclude(list = []) {
        local types = ["current", "minutely", "hourly", "daily", "alerts"];
        local matches = [];
        foreach (item in list) {
            foreach (type in types) {
                if (item == type) matches.append(item);
            }
        }

        if (matches.len() == 0) {
            if (_debug) server.error("OpenWeather.exclude() incorrect exlcusions passed");
            return this;
        }

        _excludes = "";
        foreach (item in matches) {
            _excludes += (item + ",");
        }

        if (_excludes.len() > 0) _excludes = _excludes.slice(0, _excludes.len() - 1);
        if (_debug) server.log("OpenWeather excludes set: " + _excludes);
        return this;
    }

    # *********PRIVATE FUNCTIONS - DO NOT CALL **********

    """
    Send a request to Dark Sky.

    Args:
        request_uri (string):      The HTTPS request to send.

    Returns:
        The HTTPS response, or None
    """
    def _send_request(self, request_uri):
        response = requests.get(request_uri)
        return _process_response(response)

    def _process_response(self, response):
        """
        Process a response received from OpenWeather.

        Args:
            response (response):    The HTTPS response.

        Returns
            The latest request count, or -1 on error.
        """
        out_data = None
        in_data = response.json()
        response.close()

        if in_data["statuscode"] != 200:
            err = F"Unable to retrieve forecast data (code: {in_data["statuscode"]})"
        else:
            try:
                # Have we valid JSON?
                out_data = in_data["body"]
            except:
                err = "Unable to decode data received from Open Weather"
        return {"err" : err, "data" : out_data}


    def _check_coords(self, longitude=999.0, latitude=999.0, caller="function"):
        """
        Check that valid co-ords have been supplied.

        Args:
            longitude (float):      Longitude of location for which a forecast is required.
            latitude (float):       Latitude of location for which a forecast is required.
            caller (string):        The name of the calling function, for error reporting.

        Returns:
            Whether the supplied co-ordinates are valid (True) or not (False).
        """
        try:
            longitude = float(longitude)
        except:
            if debug:
                print("OpenWeather." + caller + "() can't process supplied longitude value")
                return False

        try:
            latitude = float(latitude)
        except:
            if debug:
                print("OpenWeather." + caller + "() can't process supplied latitude value")
                return False

        if longitude == 999.0 or latitude == 999.0:
            if (debug):
                print("OpenWeather." + caller + "() requires valid latitude/longitude co-ordinates")
                return False

        if latitude > 90.0 or latitude < -90.0:
            if (debug):
                print("OpenWeather." + caller + "() requires valid a latitude co-ordinate (value out of range)")
            return False

        if longitude > 180.0 or longitude < -180.0:
            if (debug):
                print("OpenWeather." + caller + "() requires valid a latitude co-ordinate (value out of range)")
            return False
        return True


    def _add_options(self, baseurl=""):
        """
        Add URL-encoded options to the request URL. Used when assembling HTTPS requests.

        Args:
            baseurl (string):   Optional base URL.

        Returns
            The full URL with added options.
        """
        opts = "&units=" + units
        if lang: opts += "&lang=" + lang
        if excludes: opts += "&exclude=" + excludes
        return baseurl + opts
