'''
PicoWeather

Version:        1.0.0
Author:         Tony Smith (@smittytone)
License:        MIT
Copyright:      2022
'''


'''
IMPORTS
'''
import board
import busio
import rtc
from time import monotonic_ns, sleep, localtime
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogOut
from adafruit_esp32spi import adafruit_esp32spi
from ht16k33matrix import HT16K33Matrix
from openweather import OpenWeather
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket

'''
Add a `secrets.py` to your filesystem that has a dictionary called `secrets`
with the following keys:

* "ssid", "password" -- your WiFi credentials
* "apikey"           -- your Openweather API key
* "lat", "lng"       -- your decimal co-ordinates
* "tz"               -- your timezone offset (+/-) from GMT

DO NOT share that file or commit it into Git or other source control.
'''
try:
    from secrets import secrets
    if not "ssid" in secrets: raise
    if not "password" in secrets: raise
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


'''
CONSTANTS
'''
LED_R = 25
LED_G = 26
LED_B = 27
I2C_SDA = board.GP4
I2C_SCL = board.GP5
DISPLAY_PERIOD_NS = 20 * 1000000000
FORECAST_PERIOD_NS = 15 * 60 * 1000000000


'''
GLOBALS
'''
saved_data = None
iconset = {}
debug = True


'''
FUNCTIONS
'''

'''
Configure the PicoWireless' ESP32.

Returns:
    An esp32spi_control object through which the app will
    communicate with the ESP32.
'''
def setup_esp32():
    esp32_cs = DigitalInOut(board.GP7)
    esp32_ready = DigitalInOut(board.GP10)
    esp32_reset = DigitalInOut(board.GP11)
    esp32_spi = busio.SPI(board.GP18, board.GP19, board.GP16)
    return adafruit_esp32spi.ESP_SPIcontrol(esp32_spi, esp32_cs, esp32_ready, esp32_reset)


'''
Configure the HT16K33-based 8x8 LED matrix.

Returns:
    An ht16k33matrix object.
'''
def setup_display():
    # Power the matrix on GPIO 3
    pwr_pin = DigitalInOut(board.GP3)
    pwr_pin.direction = Direction.OUTPUT
    pwr_pin.value = True

    # Set up the I2C bus on GPIO 4, GPIO 5
    i2c = busio.I2C(I2C_SCL, I2C_SDA)
    while not i2c.try_lock(): pass
    display = HT16K33Matrix(i2c)

    # Set these according to your preference
    display.set_brightness(2)
    display.set_angle(2)

    # Clear the screen
    display.clear().draw()
    return display


'''
Configure the PicoWireless' A button.

Returns:
    A GPIO pin object.
'''
def setup_button_a():
    button = DigitalInOut(board.GP12)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    return button


'''
Connect the PicoWireless to WiFi.

Args:
    e [esp32spi_control]    The ESP32 interface.
    s [string]              The WiFi SSID.
    p [string]              The WiFi password.
'''
def do_connect(e, s, p):
    set_led(e, 0.5, 0.2, 0)
    while not e.is_connected:
        try:
            e.connect_AP(s, p)
        except RuntimeError as e:
            if debug:
                print("[DEBUG] Could not connect to AP, retrying: ", e)
            continue
    if debug:
        print("[DEBUG] Connected to", str(e.ssid, "utf-8"), "\tRSSI:", e.rssi)
    set_led(e, 0, 0.5, 0)


'''
Set the PicoWireless RGB LED.

Args:
    e [esp32spi_control]    The ESP32 interface.
    r [float]               A red value from 0.0 to 1.0.
    g [float]               A green value from 0.0 to 1.0.
    b [float]               A blue value from 0.0 to 1.0.
'''
def set_led(e, r, g, b):
    e.set_analog_write(LED_R, 1 - r)
    e.set_analog_write(LED_B, 1 - b)
    e.set_analog_write(LED_G, 1 - g)


'''
Display the current forecast as a string of weather condition and
temperature, followed by the weather condition icon.

Args:
    display [ht16k33matrix] The matrix display.
    display_data [dict]     The weather forecast to present.
'''
def display_weather(display, display_data=None):
    global saved_data

    # Bail if we have no data passed in
    if not display_data:
        if not saved_data:
            return
        # Use a saved forecast
        display_data = saved_data

    # Prepare the string used to display the weather forecast by name...
    scroll_text = "    " + display_data["cast"][0:1].upper() + display_data["cast"][1:] + "  "

    # ...then add the forecast temperature...
    scroll_text += ("Out: {:.1f}".format(display_data["temp"]) + "\x7F" + "c")

    # Prepare an icon to display
    try:
        icon = iconset[display_data["icon"]]
    except:
        icon = iconset["none"]

    # Display the forecast if we should display it
    display.clear()
    display.scroll_text(scroll_text + "    ", 0.08)
    saved_data = display_data

    # Pause for half a second
    sleep(0.5)

    # Display the weather icon
    display.set_character(icon).draw()


'''
Define the app's custom characters, stored in the matrix display object,
and the dictionary that binds icon names to character codes.

Args:
    display [ht16k33matrix] The matrix display
'''
def setup_icons(display):
    # Set up weather icons using user-definable characters
    display.define_character(b"\x91\x42\x18\x3d\xbc\x18\x42\x89", 0)
    display.define_character(b"\x31\x7A\x78\xFA\xFC\xF9\x7A\x30", 1)
    display.define_character(b"\x31\x7A\x78\xFA\xFC\xF9\x7A\x30", 2)
    display.define_character(b"\x28\x92\x54\x38\x38\x54\x92\x28", 3)
    display.define_character(b"\x32\x7D\x7A\xFD\xFA\xFD\x7A\x35", 4)
    display.define_character(b"\x28\x28\x28\x28\x28\xAA\xAA\x44", 5)
    display.define_character(b"\xAA\x55\xAA\x55\xAA\x55\xAA\x55", 6)
    display.define_character(b"\x30\x78\x78\xF8\xF8\xF8\x78\x30", 7)
    display.define_character(b"\x30\x48\x48\x88\x88\x88\x48\x30", 8)
    display.define_character(b"\x00\x00\x00\x0F\x38\xE0\x00\x00", 9)
    display.define_character(b"\x00\x40\x6C\xBE\xBB\xB1\x60\x40", 10)
    display.define_character(b"\x3C\x42\x81\xC3\xFF\xFF\x7E\x3C", 11)
    display.define_character(b"\x00\x00\x40\x9D\x90\x60\x00\x00", 12)

    # Set up a table to map incoming weather condition names
    # (eg. "clearday") to user-definable character Ascii values
    iconset["clearday"] = 0
    iconset["rain"] = 1
    iconset["lightrain"] = 2
    iconset["snow"] = 3
    iconset["sleet"] = 4
    iconset["wind"] = 5
    iconset["fog"] = 6
    iconset["cloudy"] = 7
    iconset["partlycloudy"] = 8
    iconset["thunderstorm"] = 9
    iconset["tornado"] = 10
    iconset["clearnight"] = 11
    iconset["none"] = 12


'''
Show the app's start-up message.

Args:
    display [ht16k33matrix] The matrix display.
'''
def show_startup(display):
    display.clear().draw()
    display.scroll_text("    PicoWeather 1.0.0    ", 0.05)
    sleep(0.5)


'''
Set the RTC using the ESP32.

Args:
    e [esp32spi_control]    The ESP32 interface.
    timezone_offset [int]   An optional +/- hour offset from GMT.

Returns:
    Whether the RTC was set (True) or not (False).
'''
def set_time(e, timezone_offset=0):
    try:
        now = e.get_time()
        now = localtime(now[0] + timezone_offset)
        rtc.RTC().datetime = now
    except ValueError as err:
        print("[ERROR] Could not set RTC: " + str(err))
        return False
    return True


'''
Set some weather test data.
'''
def get_test_data():
    test_data = {}
    test_data["icon"] = "snow"
    test_data["cast"] = "rain"
    test_data["temp"] = 11.5
    return test_data


'''
RUNTIME START
'''
# Set up the ESP32
esp32 = setup_esp32()
set_led(esp32, 0.5, 0, 0)

# Set up the display and weather icons
matrix = setup_display()
setup_icons(matrix)

# Initialize a requests object with a socket and an esp32spi interface
socket.set_interface(esp32)
requests.set_socket(socket, esp32)

# Set up Open Weather
open_weather_call_count = 0
open_weather = OpenWeather(requests, secrets["apikey"], True)
weather_data = {}
# weather_data = get_test_date()
do_show = True
is_rtc_set = False
last_check = localtime()
last_forecast = monotonic_ns()
last_display = last_forecast

# Display banner
show_startup(matrix)

# Primary loop
while True:
    if not esp32.is_connected:
        do_connect(esp32, secrets["ssid"], secrets["password"])

    # Check the clock
    ns_tick = monotonic_ns()
    if (ns_tick - last_forecast > FORECAST_PERIOD_NS or do_show) and open_weather_call_count < 990:
        # Get a forecast every FORECAST_PERIOD_NS nanoseconds
        lat = secrets["lat"] if "lat" in secrets else 0
        lng = secrets["lng"] if "lng" in secrets else 0
        forecast = open_weather.request_forecast(lat, lng)

        if "err" in forecast and debug:
            print("[ERROR] " + forecast["err"])
        elif "data" in forecast and "hourly" in forecast["data"]:
            if debug:
                print("[DEBUG] HTTP status:", forecast["data"]["statuscode"])
            # Get second item in array: this is the weather one hour from now
            item = forecast["data"]["hourly"][1]
            wid = 0
            if "weather" in item and len(item["weather"]) > 0:
                weather_data["cast"] = item["weather"][0]["main"]
                wid = item["weather"][0]["id"]
            else:
                weather_data["cast"] = "None"

            # Adjust troublesome icon names
            if wid == 771: weather_data["cast"] = "Windy"
            if wid == 871: weather_data["cast"] = "Tornado"
            if wid > 699 and wid < 770: weather_data["cast"] = "Foggy"
            weather_data["icon"] = weather_data["cast"].lower()

            if weather_data["cast"] == "Clouds":
                if wid < 804:
                    weather_data["icon"] = "partlycloudy"
                    weather_data["cast"] = "Partly cloudy"
                else:
                    weather_data["icon"] = "cloudy"
                    weather_data["cast"] = "Cloudy"

            if wid > 602 and wid < 620:
                weather_data["icon"] = "sleet"
                weather_data["cast"] = "Sleet"

            if weather_data["cast"] == "Drizzle":
                weather_data["cast"] = "lightrain"

            if weather_data["cast"] == "Clear":
                # Set clear icon by time of day
                parts = item["weather"][0]["icon"].split(".")
                diurnal = parts[0][- 1]
                if diurnal == "n":
                    weather_data["icon"] += "night"
                    weather_data["cast"] += " night"
                else:
                    weather_data["icon"] += "day"
                    weather_data["cast"] += " day"

            # Send the icon name to the device
            weather_data["temp"] = item["feels_like"]

            # Update the tally, or zero on a new day
            open_weather_call_count += 1
            now = localtime()
            if debug:
                print("[DEBUG] Day:",now[2],"API call count:",open_weather_call_count)
            if now[2] != last_check[2]:
                # A new day, so reset the call count
                open_weather_call_count = 0
            last_check = now
            last_forecast = ns_tick
            do_show = True

            # Get the current time if it's not yet set
            if not is_rtc_set:
                tz = secrets["tz"] if "tz" in secrets else 0
                is_rtc_set = set_time(esp32, tz)

    if (ns_tick - last_display > DISPLAY_PERIOD_NS) or do_show:
        # Update the display every DISPLAY_PERIOD_NS nanoseconds,
        # or on a new forecast
        display_weather(matrix, weather_data)
        do_show = False
        last_display = ns_tick
