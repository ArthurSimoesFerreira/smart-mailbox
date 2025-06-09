import network, time
from machine import Pin
from umqtt.robust import MQTTClient
import ssl
import umail

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
TOPIC_STATUS = f"pico/{DEVICE_ID}/status".encode()
TOPIC_RECEIVED = f"pico/{DEVICE_ID}/received".encode()

client = None

# Pin setup
trigger = Pin(14, Pin.OUT)
echo = Pin(15, Pin.IN)

# Mail Checking
last_distance = None
THRESHOLD = 1.5  # cm

# Email details
sender_email = 'asferreira1002@gmail.com'
sender_name = 'IOT-Mailbox'
sender_app_password = 'jgfl drsu zrlp awji'
recipient_email = 'asferreira1002@gmail.com'
email_subject = 'Your Mailbox'

# Setup LED
led = Pin("LED", Pin.OUT)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("🔌 Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
    print("✅ Wi-Fi connected:", wlan.ifconfig())
    

def send_email(msg):
    smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
    smtp.login(sender_email, sender_app_password)
    smtp.to(recipient_email)
    smtp.write("From: " + sender_name + "<" + sender_email + ">\n")
    smtp.write("Subject: " + email_subject + "\n")
    smtp.write(msg)
    smtp.send()
    smtp.quit()
    print("Email sent!")

    
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


def check_mailbox(current_distance):
    global last_distance
    status = None

    if last_distance is not None:
        diff = last_distance - current_distance
        if diff >= THRESHOLD:
            status = "Mail delivered!"
            print(status)
            led.on()
    last_distance = current_distance
    return status


def on_message(topic, msg):
    global client
    print("Received:", topic, msg)
    if topic.decode() == f"pico/{DEVICE_ID}/received" and msg.decode().strip().lower() == "yes":
        print("✅ Mail marked as received. Turning off LED.")
        led.off()
        client.publish(TOPIC_STATUS, "None")


def connect_mqtt():
    global client
    ssl_context =  create_ssl_context()
    
    client = MQTTClient(
        client_id=CLIENT_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        ssl=ssl_context,
        keepalive=10
    )
    client.set_last_will(TOPIC_PUBLISH, b"offline", retain=True)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(TOPIC_RECEIVED)
    print("Connected to secure MQTT broker (TLS)")
    return client


def main():
    global client
    connect_wifi()
    client = connect_mqtt()

    while True:
        client.check_msg()
        distance = ultra()
        if distance == -1:
            print("Sensor timeout or not connected")
            msg = "error"
        else:
            print("Distance:", distance, "cm")
            msg = str(distance)

        try:
            client.publish(TOPIC_PUBLISH, msg)
            status_msg = check_mailbox(distance)
            if status_msg is not None:
                client.publish(TOPIC_STATUS, status_msg)
                send_email(status_msg)
        except OSError as e:
            print("MQTT error:", e)
            try:
                client.disconnect()
            except:
                pass
            client = connect_mqtt()


        time.sleep(5)


main()