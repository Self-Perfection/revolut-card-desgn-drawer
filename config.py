import tomllib
import sys
import os
from ppadb.client import Client as AdbClient


def load_config():
    """Load configuration from config.toml, fallback to config.default.toml"""
    # Load defaults
    if not os.path.exists('config.default.toml'):
        print("Error: config.default.toml not found!")
        sys.exit(1)

    with open('config.default.toml', 'rb') as f:
        config = tomllib.load(f)

    # Flatten structure for backward compatibility
    flattened = {}
    if 'bounds' in config:
        flattened.update(config['bounds'])
    if 'cutoff_top_left' in config:
        flattened['cutoff_tl_x'] = config['cutoff_top_left']['x']
        flattened['cutoff_tl_y'] = config['cutoff_top_left']['y']
    if 'cutoff_bottom_right' in config:
        flattened['cutoff_br_x'] = config['cutoff_bottom_right']['x']
        flattened['cutoff_br_y'] = config['cutoff_bottom_right']['y']
    if 'settings' in config and 'scale' in config['settings']:
        flattened['scale'] = config['settings']['scale']

    # Override with user config if it exists
    if os.path.exists('config.toml'):
        with open('config.toml', 'rb') as f:
            user_config = tomllib.load(f)

        # Flatten and update
        if 'bounds' in user_config:
            flattened.update(user_config['bounds'])
        if 'cutoff_top_left' in user_config:
            flattened['cutoff_tl_x'] = user_config['cutoff_top_left']['x']
            flattened['cutoff_tl_y'] = user_config['cutoff_top_left']['y']
        if 'cutoff_bottom_right' in user_config:
            flattened['cutoff_br_x'] = user_config['cutoff_bottom_right']['x']
            flattened['cutoff_br_y'] = user_config['cutoff_bottom_right']['y']
        if 'settings' in user_config and 'scale' in user_config['settings']:
            flattened['scale'] = user_config['settings']['scale']

    return flattened


def connect_to_device():
    """Connect to Android device via ADB"""
    client = AdbClient(host="127.0.0.1", port=5037)
    devices = client.devices()

    if len(devices) == 0:
        print("No devices connected")
        sys.exit(1)

    device = devices[0]
    print(f"Connected to {device.serial}")
    return device
