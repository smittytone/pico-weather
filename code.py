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
with "ssid" and "password" keys for your WiFi credentials, "apikey" for your
Openweather API key, and "lat" and "lng" for your decimal co-ordinates.
DO NOT share that file or commit it into Git or other source control.
'''
try:
    from secrets import secrets
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
DISPLAY_PERIOD_NS = 15 * 1000000000
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
def setup_esp32():
    esp32_cs = DigitalInOut(board.GP7)
    esp32_ready = DigitalInOut(board.GP10)
    esp32_reset = DigitalInOut(board.GP11)
    esp32_spi = busio.SPI(board.GP18, board.GP19, board.GP16)
    return adafruit_esp32spi.ESP_SPIcontrol(esp32_spi, esp32_cs, esp32_ready, esp32_reset)


def setup_display():
    # Power the matrix on GPIO 3
    pwr_pin = DigitalInOut(board.GP3)
    pwr_pin.direction = Direction.OUTPUT
    pwr_pin.value = True

    # Set up the I2C bus on GPIO 4, GPIO 5
    i2c = busio.I2C(I2C_SCL, I2C_SDA)
    while not i2c.try_lock(): pass
    display = HT16K33Matrix(i2c)
    display.set_brightness(2)
    display.set_angle(2)
    display.clear().draw()
    return display


def setup_button_a():
    button = DigitalInOut(board.GP12)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    return button


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


def set_led(e, r, g, b):
    e.set_analog_write(LED_R, 1 - r)
    e.set_analog_write(LED_B, 1 - b)
    e.set_analog_write(LED_G, 1 - g)


def display_weather(matrix, display_data=None):
    """
    This function is called in response to a message from the server containing
    a new hour-ahead weather forecast, or in response to a timer-fire if the user
    has applied the 'refresh display' setting. Refreshing the display shows the
    current forecast again, and the current forecast will continue to be shown
    if the device goes offline for any period
    """
    global saved_data

    # Bail if we have no data passed in
    if not display_data:
        if not saved_data:
            return
        # Use a saved forecast
        display_data = saved_data

    # Prepare the string used to display the weather forecast by name...
    ds = "    " + display_data["cast"][0:1].upper() + display_data["cast"][1:] + "  "

    # ...then add the forecast temperature...
    ds += ("Out: {:.1f}".format(display_data["temp"]) + "\x7F" + "c")

    # Prepare an icon to display
    try:
        icon = iconset[display_data["icon"]]
    except:
        icon = iconset["none"]

    # Store the current icon and forecast string
    # (we will need to re-use it if the 'refresh display' timer fires, or
    # the device goes offline and receives no new forecasts)
    saved_data = display_data

    # Display the forecast if we should display it
    matrix.clear()
    matrix.scroll_text(ds + "    ", 0.08)

    # Pause for half a second
    sleep(0.5)

    # Display the weather icon
    matrix.set_character(icon).draw()


def setup_icons(matrix):
    # Set up weather icons using user-definable characters
    matrix.define_character(b"\x91\x42\x18\x3d\xbc\x18\x42\x89", 0)
    matrix.define_character(b"\x31\x7A\x78\xFA\xFC\xF9\x7A\x30", 1)
    matrix.define_character(b"\x31\x7A\x78\xFA\xFC\xF9\x7A\x30", 2)
    matrix.define_character(b"\x28\x92\x54\x38\x38\x54\x92\x28", 3)
    matrix.define_character(b"\x32\x7D\x7A\xFD\xFA\xFD\x7A\x35", 4)
    matrix.define_character(b"\x28\x28\x28\x28\x28\xAA\xAA\x44", 5)
    matrix.define_character(b"\xAA\x55\xAA\x55\xAA\x55\xAA\x55", 6)
    matrix.define_character(b"\x30\x78\x78\xF8\xF8\xF8\x78\x30", 7)
    matrix.define_character(b"\x30\x48\x48\x88\x88\x88\x48\x30", 8)
    matrix.define_character(b"\x00\x00\x00\x0F\x38\xE0\x00\x00", 9)
    matrix.define_character(b"\x00\x40\x6C\xBE\xBB\xB1\x60\x40", 10)
    matrix.define_character(b"\x3C\x42\x81\xC3\xFF\xFF\x7E\x3C", 11)
    matrix.define_character(b"\x00\x00\x40\x9D\x90\x60\x00\x00", 12)

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


"""
This function sets the matrix pixels from the outside in, in a spiral pattern
"""
def app_intro(matrix):
    x = 7
    y = 0
    dx = 0
    dy = 1
    mx = 6
    my = 7
    nx = 0
    ny = 0

    for i in range(0, 64):
        matrix.plot(x, y, 1).draw()

        if dx == 1 and x == mx:
            dy = 1
            dx = 0
            mx -= 1
        elif dx == -1 and x == nx:
            nx += 1
            dy = -1
            dx = 0
        elif dy == 1 and y == my:
            dy = 0
            dx = -1
            my -= 1
        elif dy == -1 and y == ny:
            dx = 1
            dy = 0
            ny += 1

        x += dx
        y += dy
        sleep(0.015)

"""
This function clears the matrix pixels from the inside out, in a spiral pattern
"""
def app_outro(matrix):
    x = 4
    y = 3
    dx = -1
    dy = 0
    mx = 5
    my = 4
    nx = 3
    ny = 2

    for i in range(0, 64):
        matrix.plot(x, y, 0).draw()

        if dx == 1 and x == mx:
            dy = -1
            dx = 0
            mx += 1
        elif dx == -1 and x == nx:
            nx -= 1
            dy = 1
            dx = 0
        elif dy == 1 and y == my:
            dy = 0
            dx = 1
            my += 1
        elif dy == -1 and y == ny:
            dx = -1
            dy = 0
            ny -= 1

        x += dx
        y += dy
        sleep(0.015)


def get_time(timeout=10):
    # https://github.com/micropython/micropython/blob/master/ports/esp8266/modules/ntptime.py
    # Modify the standard code to extend the timeout, and catch OSErrors triggered when the
    # socket operation times out
    ntp_query = bytearray(48)
    ntp_query[0] = 0x1b
    address = socket.getaddrinfo("pool.ntp.org", 123)[0][-1]
    # Create DGRAM UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    return_value = None
    try:
        _ = sock.sendto(ntp_query, address)
        msg = sock.recv(48)
        val = struct.unpack("!I", msg[40:44])[0]
        return_value = val - 3155673600
    except:
        pass
    sock.close()
    return return_value


def set_rtc(timeout=10):
    now_time = get_time(timeout)
    if now_time:
        time_data = localtime(now_time)
        time_data = time_data[0:3] + (0,) + time_data[3:6] + (0,)
        RTC().datetime(time_data)
        return True
    return False


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
do_show = True
is_rtc_set = False
last_check = localtime()

"""
# Test data
weather_data["icon"] = "rain"
weather_data["cast"] = "rain"
weather_data["temp"] = 11.5
"""

"""
# Display banner
matrix.clear().draw()
matrix.scroll_text("    PicoWeather 1.0.0    ", 0.08)
sleep(0.5)
app_intro(matrix)
app_outro(matrix)
"""

# Primary loop
while True:
    if not esp32.is_connected:
        do_connect(esp32, secrets["ssid"], secrets["password"])
        is_rtc_set = set_rtc()
        if debug and is_rtc_set:
            print("[DEBUG] RTC set")

    # Check the clock
    ns_tick = monotonic_ns()
    if (ns_tick % FORECAST_PERIOD_NS == 0 or do_show) and open_weather_call_count < 990:
        # Get a forecast every 15 mins
        forecast = open_weather.request_forecast(secrets["lat"], secrets["lng"])
        if "err" in forecast and debug:
            print("[ERROR] " + forecast["err"])
        elif "data" in forecast and "hourly" in forecast["data"]:
            if debug:
                print("[DEBUG] HTTP status:", forecast["data"]["statuscode"])
            # Get second item in array: this is the weather one hour from now
            item = forecast["data"]["hourly"][0]
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
            do_show = True

    if ns_tick % DISPLAY_PERIOD_NS == 0 or do_show:
        # Update the display every 2 mins, or on a new forecast
        display_weather(matrix, weather_data)
        do_show = False
