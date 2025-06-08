devices = {}

def add_device(device_id):
    if device_id in devices:
        return False
    devices[device_id] = {
        "distance": None,
        "status": "Unknown"
    }
    return True

def remove_device(device_id):
    return devices.pop(device_id, None)

def update_device_data(device_id, distance=None, status=None):
    if device_id not in devices:
        add_device(device_id)

    if distance is not None:
        devices[device_id]["distance"] = distance
    if status is not None:
        devices[device_id]["status"] = status

def get_device(device_id):
    return devices.get(device_id)

def list_devices():
    return devices
