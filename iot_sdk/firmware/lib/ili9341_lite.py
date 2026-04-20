# MicroPython ILI9341 Lite Driver (SPI)
# Simple driver for TFT 320x240 screens in Wokwi/ESP32

import time
import ustruct
from machine import Pin

class ILI9341:
    def __init__(self, spi, cs, dc, rst, width=240, height=320):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        
        self.rst.value(1)
        time.sleep_ms(5)
        self.rst.value(0)
        time.sleep_ms(20)
        self.rst.value(1)
        time.sleep_ms(150)

        for cmd, data in [
            (0xEF, b'\x03\x80\x02'),
            (0xCF, b'\x00\xC1\x30'),
            (0xED, b'\x64\x03\x12\x81'),
            (0xE8, b'\x85\x00\x78'),
            (0xCB, b'\x39\x2C\x00\x34\x02'),
            (0xF7, b'\x20'),
            (0xEA, b'\x00\x00'),
            (0xC0, b'\x23'), # Power control
            (0xC1, b'\x10'), # Power control
            (0xC5, b'\x3e\x28'), # VCM control
            (0xC7, b'\x86'), # VCM control2
            (0x36, b'\x48'), # Memory Access Control (Orientation)
            (0x3A, b'\x55'), # Pixel Format
            (0xB1, b'\x00\x18'), # Frame Rate
            (0xB6, b'\x08\x82\x27'), # Display Function Control
            (0xF2, b'\x00'), # 3Gamma Function Disable
            (0x26, b'\x01'), # Gamma curve selected
            (0xE0, b'\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00'),
            (0xE1, b'\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F'),
            (0x11, None), # Exit Sleep
            (0x29, None), # Display on
        ]:
            self.write_cmd(cmd, data)

    def write_cmd(self, cmd, data=None):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)
        if data:
            self.write_data(data)

    def write_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(data)
        self.cs.value(1)

    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A, ustruct.pack(">HH", x0, x1))
        self.write_cmd(0x2B, ustruct.pack(">HH", y0, y1))
        self.write_cmd(0x2C)

    def fill_rect(self, x, y, w, h, color):
        x = min(self.width - 1, max(0, x))
        y = min(self.height - 1, max(0, y))
        w = min(self.width - x, w)
        h = min(self.height - y, h)
        self.set_window(x, y, x + w - 1, y + h - 1)
        chunk_size = 1024
        color_bytes = ustruct.pack(">H", color) * (chunk_size // 2)
        full_chunks, remainder = divmod(w * h * 2, chunk_size)
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(full_chunks):
            self.spi.write(color_bytes)
        if remainder:
            self.spi.write(color_bytes[:remainder])
        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    @staticmethod
    def color565(r, g, b):
        return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3
