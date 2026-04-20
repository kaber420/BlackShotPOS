import time
import machine
from lib.bs_client import BlackshotClient

# CONFIGURACIÓN DEL DISPOSITIVO
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""
SERVER_HOST = "10.0.2.2"  # IP especial de Wokwi para acceder al localhost del host
SERVER_PORT = 8000
DEVICE_TOKEN = "CAMBIA_POR_TU_TOKEN"

# SELECCIÓN DE PANTALLA (Activa uno según tu diagram.json)
SCREEN_TYPE = "OLED" # "OLED" o "TFT"

display = None

def setup_display():
    global display
    if SCREEN_TYPE == "OLED":
        from lib.ssd1306 import SSD1306_I2C
        i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
        display = SSD1306_I2C(128, 64, i2c)
        display.text("Blackshot IoT", 10, 10)
        display.text("Starting...", 10, 30)
        display.show()
    elif SCREEN_TYPE == "TFT":
        from lib.ili9341_lite import ILI9341
        spi = machine.SPI(1, baudrate=40000000, sck=machine.Pin(18), mosi=machine.Pin(23))
        cs = machine.Pin(15, machine.Pin.OUT)
        dc = machine.Pin(2, machine.Pin.OUT)
        rst = machine.Pin(4, machine.Pin.OUT)
        display = ILI9341(spi, cs, dc, rst)
        display.fill(0)
        # Nota: ili9341_lite es básico, para texto requeriría un font renderer.
        # Por ahora solo llenamos la pantalla de color como prueba.
        display.fill(display.color565(0, 0, 255)) # Azul

def on_ready(msg):
    print("NOTIFICACIÓN RECIBIDA:", msg)
    if SCREEN_TYPE == "OLED" and display:
        display.fill(0)
        display.text("ORDEN LISTA!", 10, 10)
        display.text(msg[:15], 10, 30)
        display.show()
        time.sleep(5)
        display.fill(0)
        display.text("Blackshot POS", 10, 10)
        display.show()

def main():
    setup_display()
    
    client = BlackshotClient(SERVER_HOST, SERVER_PORT, DEVICE_TOKEN)
    client.on_ready_callback = on_ready
    
    client.connect_wifi(WIFI_SSID, WIFI_PASS)
    
    if client.connect_ws():
        if display and SCREEN_TYPE == "OLED":
            display.fill(0)
            display.text("CONECTADO", 10, 10)
            display.show()
            
        last_health = 0
        while True:
            client.check_messages()
            
            # Reportar salud cada 60 segundos
            if time.time() - last_health > 60:
                client.report_health(battery=95, rssi=-50)
                last_health = time.time()
                
            time.sleep(0.1)

if __name__ == "__main__":
    main()
