# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pure-python-adb>=0.3.0.dev0",
#     "numpy>=1.21.0",
#     "Pillow>=8.0.0",
# ]
# ///

from ppadb.client import Client as AdbClient
import numpy as np
import time
from PIL import Image
import sys
import argparse

def extract_continuous_swipes(image_array):
    swipe_data = []
    height, width = image_array.shape
    for y in range(height - 1, -1, -1):  # Start from the bottom row
        row = image_array[y]
        start = None
        for x in range(width):
            if row[x] == 255:  # White pixel
                if start is None:
                    start = x
            else:
                if start is not None:
                    swipe_data.append((start, x - 1, height - 1 - y))  # Invert y-coordinate
                    start = None
        if start is not None:
            swipe_data.append((start, width - 1, height - 1 - y))  # Invert y-coordinate
    return swipe_data

def swipe(device, start_x, end_x, y, config):
    duration = 1000

    # Check if start point is within bounds
    if not is_within_bounds(start_x, y, config):
        return

    # Check if end point is within bounds, clip if needed
    if not is_within_bounds(end_x, y, config):
        # Clip to right boundary
        end_x = min(end_x, config['right_x'])

    device.shell(f"input swipe {start_x} {y} {end_x} {y} {duration}")
    time.sleep(0.01)  # Small delay between swipes

def connect_to_device():
    client = AdbClient(host="127.0.0.1", port=5037)
    devices = client.devices()

    if len(devices) == 0:
        print("No devices connected")
        sys.exit(1)

    device = devices[0]
    print(f"Connected to {device.serial}")
    return device


def parse_toml_config(filename):
    """Simple TOML parser for our basic config format"""
    config = {}
    with open(filename, 'r') as f:
        section = None
        for line in f:
            line = line.strip()
            if line.startswith('['):
                section = line[1:-1]
            elif '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Try to parse as number
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except:
                    pass
                if section == 'bounds':
                    config[key] = value
                elif section == 'cutoff_top_left':
                    config[f'cutoff_tl_{key}'] = value
                elif section == 'cutoff_bottom_right':
                    config[f'cutoff_br_{key}'] = value
                elif section == 'settings' and key == 'scale':
                    config['scale'] = value
    return config


def load_config():
    """Load configuration from config.toml, fallback to config.default.toml"""
    import os

    # Load defaults
    if not os.path.exists('config.default.toml'):
        print("Error: config.default.toml not found!")
        sys.exit(1)

    config = parse_toml_config('config.default.toml')

    # Override with user config if it exists
    if os.path.exists('config.toml'):
        user_config = parse_toml_config('config.toml')
        config.update(user_config)

    return config


def is_within_bounds(x, y, config):
    """Check if point is within drawing area (considering cutoffs)"""
    # Outside main rectangle
    if x < config['left_x'] or x > config['right_x']:
        return False
    if y < config['top_y'] or y > config['bottom_y']:
        return False

    # Inside top-left cutoff (excluded)
    if x < config['cutoff_tl_x'] and y < config['cutoff_tl_y']:
        return False

    # Inside bottom-right cutoff (excluded)
    if x > config['cutoff_br_x'] and y > config['cutoff_br_y']:
        return False

    return True


def draw_image(device, image_path, step=1):
    # Load configuration
    config = load_config()

    # Load and process the image
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    image_array = np.array(image)
    image_array = (image_array < 128).astype(np.uint8) * 255  # Binarize the image

    # Extract swipe data
    swipe_data = extract_continuous_swipes(image_array)

    # Filter swipe data by step if needed
    if step > 1:
        # Get unique Y coordinates and sort them
        unique_y = sorted(set(y for _, _, y in swipe_data))
        # Select every Nth Y coordinate
        selected_y = set(unique_y[i] for i in range(0, len(unique_y), step))
        # Filter swipe data to keep only selected rows
        swipe_data = [(x1, x2, y) for x1, x2, y in swipe_data if y in selected_y]

    # Map image coordinates to screen coordinates using config
    screen_start_x = config['left_x']
    screen_start_y = config['bottom_y']
    scale = config['scale']

    total_swipes = len(swipe_data)
    if step > 1:
        print(f"Drawing every {step} row(s)")
    print(f"Total swipes to perform: {total_swipes}")
    skip = 0
    # Draw the image using swipe gestures
    for i, (start_x, end_x, y) in enumerate(swipe_data, 1):
        if i < skip:
            continue
        screen_x1 = screen_start_x + start_x * scale
        screen_x2 = screen_start_x + end_x * scale
        screen_y = screen_start_y - y * scale  # Subtract y to draw from bottom to top
        swipe(device, int(screen_x1), int(screen_x2), int(screen_y), config)

        # Log progress
        if i % 10 == 0 or i == total_swipes:
            progress = (i / total_swipes) * 100
            print(f"Progress: {progress:.2f}% ({i}/{total_swipes} swipes)")

    print("Drawing completed")

def main():
    parser = argparse.ArgumentParser(description='Draw images on Android device using ADB')
    parser.add_argument('image_path', help='Path to image file')
    parser.add_argument('--step', type=int, default=1,
                       help='Draw every Nth row (default: 1 - all rows)')
    args = parser.parse_args()

    device = connect_to_device()
    draw_image(device, args.image_path, step=args.step)

if __name__ == "__main__":
    main()
