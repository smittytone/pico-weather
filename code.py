'''
IMPORTS
'''
import board
import busio
from time import monotonic_ns, sleep
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
Openweather API key.
DO NOT share that file or commit it into Git or other source control.
'''
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

'''
GLOBALS
'''
LED_R = 25
LED_G = 26
LED_B = 27
I2C_SDA = board.GP4
I2C_SCL = board.GP5

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
    display.clear()
    return display


def setup_button_a():
    button = DigitalInOut(board.GP12)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    return button


def do_connect(e, s, p):
    set_led(e, 0.5, 0.3, 0)
    while not e.is_connected:
        try:
            e.connect_AP(s, p)
        except RuntimeError as e:
            if debug: print("Could not connect to AP, retrying: ", e)
            continue
    if debug: print("Connected to", str(e.ssid, "utf-8"), "\tRSSI:", e.rssi)
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
    print(icon)
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
weather_data = {}
# Test data
weather_data["icon"] = "rain"
weather_data["cast"] = "rain"
weather_data["temp"] = 11.5

open_weather = OpenWeather(requests, secrets["apikey"], True)

do_show = True

# Primary loop
while True:
    if not esp32.is_connected:
        do_connect(esp32, secrets["ssid"], secrets["password"])

    # Check the clock
    now = monotonic_ns()
    if now % 900000000000 == 0 or do_show:
        # Get a forecast every 15 mins
        forecast = open_weather.request_forecast(secrets["lat"], secrets["lng"])
        if "err" in forecast and debug:
            print(forecast["err"])
        elif "data" in forecast and "hourly" in forecast["data"]:
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
                diurnal = parts[0][:len(parts[0]) - 1]
                if diurnal == "d":
                    weather_data["icon"] += "day"
                    weather_data["cast"] += " day"
                else:
                    weather_data["icon"] += "night"
                    weather_data["cast"] += " night"

            # Send the icon name to the device
            weather_data["temp"] = item["feels_like"]

            # Update the tally, or zero on a new day
            open_weather_call_count += 1
            do_show = True

    if now % 15000000000 == 0 or do_show:
        # Update the display every 2 mins, or on a new forecast
        display_weather(matrix, weather_data)
        do_show = False
