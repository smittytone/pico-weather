'''
PicoWeather
MicroPython version for Raspberry Pi Pico W

Version:        2.0.0.m
Author:         Tony Smith (@smittytone)
License:        MIT
Copyright:      2022
'''

'''
IMPORTS
'''
import network
import usocket as socket
import ustruct as struct
from machine import Pin, I2C, RTC
from time import ticks_us, sleep, localtime
from micropython import const
from ht16k33matrix import HT16K33Matrix
from openweather import OpenWeather

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
    print("[ERROR] WiFi credentials are stored in `secrets.py`, please add them there")
    raise


'''
CONSTANTS
'''
I2C_SDA = Pin(4)
I2C_SCL = Pin(5)
DISPLAY_PERIOD_US = 20 * 1000000
FORECAST_PERIOD_US = 15 * 60 * 1000000
CONNECT_TIMEOUT_S = 20


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
Configure the HT16K33-based 8x8 LED matrix.

Returns:
    An ht16k33matrix object.
'''
def setup_display():
    # Power the matrix on GPIO 3
    pwr_pin = Pin(3, Pin.OUT, value=1)

    # Set up the I2C bus on GPIO 4, GPIO 5
    i2c = I2C(0, scl=I2C_SCL, sda=I2C_SDA)
    display = HT16K33Matrix(i2c)

    # Set these according to your preference
    display.set_brightness(2)
    display.set_angle(2)

    # Clear the screen
    display.clear().draw()
    return display


'''
Connect the Pico W to WiFi.

Args:
    w [wlan]    The ESP32 interface.
    s [string]  The WiFi SSID.
    p [string]  The WiFi password.

Returns:
    Connection made (True) or connection error (False).
'''
def do_connect(w, s, p):
    debug_print("Attempting to connect to WiFi")
    led.off()
    w.connect(s, p)
    max_wait_s = CONNECT_TIMEOUT_S
    while max_wait_s > 0:
        if w.status() < 0 or w.status() >= 3:
            break
        max_wait_s -= 1
        led.toggle()
        sleep(1)

    if w.status() == 3:
        debug_print("Connected to WiFi")
        led.on()
        return True

    debug_print("Failed to connect to WiFi")
    flash_led(5)
    led.off()
    return False


'''
Flash the Pico W LED a number of times.

Args:
    count [int] The number of flashes.
'''
def flash_led(count):
    led.off()
    sleep(0.5)
    for i in range(0, count):
        led.on()
        sleep(0.25)
        led.off()
        sleep(0.25)


'''
Issue a UDP NTP request to get the time.

Args:
    timeout [int]   An optional timeout. Default: 10 seconds.

Returns:
    The time as an epoch timestamp, or None on error.
'''
def get_time(timeout=10):
    ntp_query = bytearray(48)
    ntp_query[0] = 0x1b
    address = socket.getaddrinfo("pool.ntp.org", 123)[0][-1]
    # Create UDP DGRAM
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    return_value = None
    err = 0
    try:
        err = 1
        _ = sock.sendto(ntp_query, address)
        err = 2
        msg = sock.recv(48)
        err = 3
        val = struct.unpack("!I", msg[40:44])[0]
        return_value = val - 3155673600
    except:
        error_print("Could not set NTP", err)
    sock.close()
    return return_value


'''
Set the Pico W's RTC.

Args:
    timezone_offset [int]   An optional +/- hour offset from GMT.
    timeout [int]           An optional NTP check timeout. Default: 10 seconds.

Returns:
    Whether the RTC was set (True) or not (False).
'''
def set_rtc(timezone_offset=0, timeout=10):
    # Make an NTP call to get the time
    now_time = get_time(timeout)
    # Set the RTC if we have a time
    if now_time is not None:
        time_data = localtime(now_time)
        time_data = time_data[0:3] + (0,) + time_data[3:6] + (0,)
        RTC().datetime(time_data)
        return True
    return False


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
    display.scroll_text(scroll_text + "    ", 0.07)
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
    display.scroll_text("    PicoWeather 2.1.0 by @smittytone    ", 0.05)
    sleep(0.5)


'''
Set some weather test data.
'''
def get_test_data():
    test_data = {}
    test_data["icon"] = "snow"
    test_data["cast"] = "rain"
    test_data["temp"] = 11.5
    return test_data


def debug_print(*args):
    if debug:
        print("[DEBUG]", fix(args))


def error_print(*args):
    print("[ERROR]", fix(args))


def fix(a):
    m = ""
    for i in a: m += (str(i) + " ")
    return m

'''
RUNTIME START
'''
# Set up the display and weather icons
matrix = setup_display()
setup_icons(matrix)

# Set up the on-board LED
led = Pin("LED", Pin.OUT, value=0)

# Initialize the Pico W's WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Set up Open Weather
open_weather_call_count = 0
open_weather = OpenWeather(secrets["apikey"], True)
weather_data = {}
# weather_data = get_test_data()
do_show = True
is_rtc_set = False
last_check = localtime()
last_forecast = ticks_us()
last_display = last_forecast

# Display banner
show_startup(matrix)

# Primary loop
while True:
    if not wlan.isconnected():
        result = do_connect(wlan, secrets["ssid"], secrets["password"])
        if not result:
            sleep(0.5)
            continue
    else:
        led.on()

    # Check the clock
    us_tick = ticks_us()
    if (us_tick - last_forecast > FORECAST_PERIOD_US or do_show) and open_weather_call_count < 990:
        # Get a forecast every FORECAST_PERIOD_US microseconds
        lat = secrets["lat"] if "lat" in secrets else 0
        lng = secrets["lng"] if "lng" in secrets else 0
        forecast = open_weather.request_forecast(lat, lng)

        if "err" in forecast and debug:
            error_print(forecast["err"])
        elif "data" in forecast and "hourly" in forecast["data"]:
            debug_print("HTTP status:", forecast["data"]["statuscode"])
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
            if 699 < wid < 770: weather_data["cast"] = "Foggy"
            weather_data["icon"] = weather_data["cast"].lower()

            if weather_data["cast"] == "Clouds":
                if wid < 804:
                    weather_data["icon"] = "partlycloudy"
                    weather_data["cast"] = "Partly cloudy"
                else:
                    weather_data["icon"] = "cloudy"
                    weather_data["cast"] = "Cloudy"

            if 602 < wid < 620:
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

            # Get the current time if it's not yet set
            if not is_rtc_set:
                tz = secrets["tz"] if "tz" in secrets else 0
                is_rtc_set = set_rtc(tz)

            # Update the tally, or zero on a new day
            open_weather_call_count += 1
            now = localtime()
            debug_print("Day:",now[2],"API call count:",open_weather_call_count)
            if now[2] != last_check[2]:
                # A new day, so reset the call count
                open_weather_call_count = 0
            last_check = now
            last_forecast = us_tick
            do_show = True

    if (us_tick - last_display > DISPLAY_PERIOD_US) or do_show:
        # Update the display every DISPLAY_PERIOD_US microseconds,
        # or on a new forecast
        display_weather(matrix, weather_data)
        last_display = us_tick
        do_show = False
        now = localtime()
        time = "{:2d}:{:2d}:{:2d}".format(now[3], now[4], now[5])
        debug_print("Re-display @:",time)
