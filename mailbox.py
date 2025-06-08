import network, time
from machine import Pin
from umqtt.simple import MQTTClient
import ssl

# Wi-Fi credentials
WIFI_SSID = 'iphone'
WIFI_PASSWORD = '10111010'

# MQTT setup
MQTT_BROKER = 'broker.emqx.io'
MQTT_PORT = 8883
MQTT_USER = 'user'
MQTT_PASSWORD = 'password'
CLIENT_ID = 'pico-w-client'
DEVICE_ID = 'mailbox1'
CA_CERTS_PATH = './ca.der'
TOPIC_PUBLISH = f"pico/{DEVICE_ID}/distance".encode()

# Pin setup
trigger = Pin(14, Pin.OUT)
echo = Pin(15, Pin.IN)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("🔌 Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print("✅ Wi-Fi connected:", wlan.ifconfig())
    
def create_ssl_context():
    # Create an SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_verify_locations(CA_CERTS_PATH)
    return ssl_context

def ultra():
    trigger.low()
    time.sleep_us(2)
    trigger.high()
    time.sleep_us(5)
    trigger.low()

    timeout = 1000000
    start = time.ticks_us()

    while echo.value() == 0:
        signaloff = time.ticks_us()
        if time.ticks_diff(signaloff, start) > timeout:
            return -1

    while echo.value() == 1:
        signalon = time.ticks_us()
        if time.ticks_diff(signalon, start) > timeout:
            return -1

    timepassed = signalon - signaloff
    distance = (timepassed * 0.0343) / 2
    return round(distance, 2)

def connect_mqtt():
    ssl_context =  create_ssl_context()
    
    client = MQTTClient(
        client_id=CLIENT_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        ssl=ssl_context
    )
    client.set_last_will(TOPIC_PUBLISH, b"offline", retain=True)
    client.connect()
    print("🔐 Connected to secure MQTT broker (TLS)")
    return client

def main():
    connect_wifi()
    client = connect_mqtt()

    while True:
        distance = ultra()
        if distance == -1:
            print("⚠️ Sensor timeout or not connected")
            msg = "error"
        else:
            print("📦 Distance:", distance, "cm")
            msg = str(distance)

        client.publish(TOPIC_PUBLISH, msg)
        time.sleep(5)

main()