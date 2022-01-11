# Pico Weather 1.0.0

A Raspberry Pi Pico-based weather readout using the Pimoroni PicoWireless.

## Hardware

* Raspberry Pi Pico with [CircuitPython installed](https://circuitpython.org/board/raspberry_pi_pico/).
* [Pimoroni PicoWireless](https://shop.pimoroni.com/products/pico-wireless-pack).
* [HT16K33-based 8x8 LED Matrix plus I2C backpack](https://www.adafruit.com/product/870)
* Male header.
* Female-to-female DuPont jumper wires.

### Hardware Setup

This is slightly tricky because the PicoWireless docks onto a Pico with male header pins.

When you solder on the male header to the Pico, **do not solder pins 5, 6, 7 and 8. When you have done, carefully push the unsoldered header pins up so that they rise up above the upper side of the Pico. Now solder the base of each pin to the Pico.

Solder the LED matrix to the backpack, and the backpack to male header as [described here]().

Now fit the Pico into the PicoWireless’ female header, taking care to get the correct orientation: the Pico’s USB connector should be at the same end as the PicoWireless’ MicroSD slot and USB print.

Now commect