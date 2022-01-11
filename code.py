# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# adafruit_requests usage with an esp32spi_socket
import board
import busio
import time
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogOut
from adafruit_esp32spi import adafruit_esp32spi
from ht16k33matrix import HT16K33Matrix
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket


def set_led(r, g, b):
    esp.set_analog_write(LED_R, 1 - r)
    esp.set_analog_write(LED_B, 1 - b)
    esp.set_analog_write(LED_G, 1 - g)

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.GP7)
esp32_ready = DigitalInOut(board.GP10)
esp32_reset = DigitalInOut(board.GP11)

spi = busio.SPI(board.GP18, board.GP19, board.GP16)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

LED_R = 25
LED_G = 26
LED_B = 27

set_led(0.5,0,0)

BUTTON_A = DigitalInOut(board.GP12)
BUTTON_A.direction = Direction.INPUT
BUTTON_A.pull = Pull.UP

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("Could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
set_led(0,0.5,0)


# Initialize a requests object with a socket and esp32spi interface
socket.set_interface(esp)
requests.set_socket(socket, esp)

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_GET_URL = "https://agent.electricimp.com/k1PYg-Rrw88i/current" #"https://httpbin.org/get"
JSON_POST_URL = "https://httpbin.org/post"

keys = ["mc", "ssid", "nm", "gw", "ip", "wip"]
key_titles = ["MAC", "SSID", "Netmask", "Gateway", "LAN IP", "WAN IP"]
key_index = 0

assert(len(keys) == len(key_titles))

while True:
    '''
    print("Fetching text from %s" % TEXT_URL)
    response = requests.get(TEXT_URL)
    print("-" * 40)

    print("Text Response: ", response.text)
    print("-" * 40)
    response.close()
    '''
    print("Fetching JSON data from %s" % JSON_GET_URL)
    response = requests.get(JSON_GET_URL)

    print(key_titles[key_index], "->", response.json()[keys[key_index]])
    response.close()

    '''
    data = "31F"
    print("POSTing data to {0}: {1}".format(JSON_POST_URL, data))
    response = requests.post(JSON_POST_URL, data=data)
    print("-" * 40)

    json_resp = response.json()
    # Parse out the 'data' key from json_resp dict.
    print("Data received from server:", json_resp["data"])
    print("-" * 40)
    response.close()

    json_data = {"Date": "July 25, 2019"}
    print("POSTing data to {0}: {1}".format(JSON_POST_URL, json_data))
    response = requests.post(JSON_POST_URL, json=json_data)
    print("-" * 40)

    json_resp = response.json()
    # Parse out the 'json' key from json_resp dict.
    print("JSON Data received from server:", json_resp["json"])
    print("-" * 40)
    response.close()
    '''

    while True:
        if BUTTON_A.value == False:
            key_index += 1
            if key_index >= len(keys): key_index = 0
            break
        time.sleep(0.01)
