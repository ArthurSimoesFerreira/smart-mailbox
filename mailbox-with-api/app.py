from flask import Flask, jsonify, request, render_template
from flask_mqtt import Mqtt
import config
import devices
import mqtt_client

app = Flask(__name__)

# Configuração MQTT
app.config.from_object(config)
mqtt = Mqtt(app)

@app.route('/')
def index():
    return jsonify({"message": "IoT Mailbox API is running!"})

@app.route('/dashboard')
def dashboard():
    return render_template('index.html')

@app.route('/devices', methods=['GET'])
def get_all_devices():
    return jsonify(devices.list_devices())

@app.route('/devices/<device_id>', methods=['GET'])
def get_single_device(device_id):
    device = devices.get_device(device_id)
    if device is None:
        return jsonify({"error": "Device not found"}), 404
    return jsonify(device)

@app.route('/devices', methods=['POST'])
def register_device():
    data = request.get_json()
    device_id = data.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400
    if not devices.add_device(device_id):
        return jsonify({"error": "Device already exists"}), 400
    return jsonify({"message": f"Device {device_id} registered."}), 201

@app.route('/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    removed = devices.remove_device(device_id)
    if removed is None:
        return jsonify({"error": "Device not found"}), 404
    return jsonify({"message": f"Device {device_id} removed."})

@app.route('/devices/<device_id>/command', methods=['POST'])
def send_command(device_id):
    data = request.get_json()
    command = data.get("command")
    if command is None:
        return jsonify({"error": "command is required"}), 400
    mqtt.publish(f"pico/{device_id}/command", command)
    return jsonify({"message": f"Command sent to {device_id}"}), 200

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode()

    try:
        parts = topic.split('/')
        if len(parts) == 3 and parts[0] == "pico":
            device_id = parts[1]
            category = parts[2]
            if category == "distance":
                devices.update_device_data(device_id, distance=payload)
            elif category == "status":
                devices.update_device_data(device_id, status=payload)
    except Exception as e:
        print(f"Error handling message: {e}")

if __name__ == '__main__':
    mqtt.subscribe('pico/+/distance')
    mqtt.subscribe('pico/+/status')
    app.run(host="0.0.0.0", port=5000, debug=True)
