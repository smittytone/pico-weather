'''
IMPORTS
'''
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogOut
from adafruit_esp32spi import adafruit_esp32spi
from ht16k33matrix import HT16K33Matrix
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import open_weather

'''
Add a `secrets.py` to your filesystem that has a dictionary called `secrets`
with "ssid" and "password" keys for your WiFi credentials.
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
    i2c = busio.I2C(board.GP7, board.GP6)
    while not i2c.try_lock(): pass
    display = HT16K33Matrix(i2c)
    display.set_brightness(2)
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
            print("Could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(e.ssid, "utf-8"), "\tRSSI:", e.rssi)
    set_led(0, 0.5, 0)




def set_led(e, r, g, b):
    e.set_analog_write(LED_R, 1 - r)
    e.set_analog_write(LED_B, 1 - b)
    e.set_analog_write(LED_G, 1 - g)


'''
RUNTIME START
'''
# Set up the ESP32
esp32 = setup_esp32()
set_led(esp32, 0.5, 0, 0)

# Set up the display
matrix = setup_display()

# Initialize a requests object with a socket and an esp32spi interface
socket.set_interface(esp32)
requests.set_socket(socket, esp32)

# Set up Open Weather
open_weather_call_count = 0
weather_data = {}
open_weather = OpenWeather(requests, secrets)

# Primary loop
while True:
    if not esp32.is_connected:
        do_connect(esp32, secrets["ssid"], secrets["password"])

    data = open_weather.request_forecast()
    if "hourly" in data:
        # Get second item in array: this is the weather one hour from now
        item = data.hourly[1]
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
            parts = item.weather[0].icon.split(".")
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
        now = date()
        if now.day != last_check.day: open_weather_call_count = 0
        lastCheck = now

    time.sleep(60 * 5)
