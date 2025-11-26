# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pure-python-adb>=0.3.0.dev0",
#     "numpy>=1.21.0",
#     "Pillow>=8.0.0",
#     "tqdm>=4.65.0",
# ]
# ///

from ppadb.client import Client as AdbClient
import numpy as np
import time
from PIL import Image
import sys
import argparse
from tqdm import tqdm

def extract_continuous_swipes(image_array):
    swipe_data = []
    height, width = image_array.shape
    for y in range(height - 1, -1, -1):  # Start from the bottom row
        row = image_array[y]
        inverted_y = height - 1 - y
        start = None
        for x in range(width):
            if row[x] == 255:  # White pixel
                if start is None:
                    start = x
            else:
                if start is not None:
                    # Alternate swipe direction: even rows left-to-right, odd rows right-to-left
                    if inverted_y % 2 == 0:
                        swipe_data.append((start, x - 1, inverted_y))
                    else:
                        swipe_data.append((x - 1, start, inverted_y))  # Swapped direction
                    start = None
        if start is not None:
            # Alternate swipe direction: even rows left-to-right, odd rows right-to-left
            if inverted_y % 2 == 0:
                swipe_data.append((start, width - 1, inverted_y))
            else:
                swipe_data.append((width - 1, start, inverted_y))  # Swapped direction
    return swipe_data

def swipe(device, start_x, end_x, y, config, min_duration=200, delay_ms=25, debug=False):
    original_start = start_x
    original_end = end_x

    # Clip start_x to valid bounds
    start_x = max(start_x, config['left_x'])
    if y < config['cutoff_tl_y']:
        start_x = max(start_x, config['cutoff_tl_x'])

    # Clip end_x to valid bounds
    end_x = min(end_x, config['right_x'])
    if y > config['cutoff_br_y']:
        end_x = min(end_x, config['cutoff_br_x'])

    # Verify both points are valid (support both directions)
    if start_x == end_x:
        return
    if not is_within_bounds(start_x, y, config):
        return
    if not is_within_bounds(end_x, y, config):
        return

    # Calculate dynamic duration based on swipe length (absolute value for both directions)
    # Formula: min_duration (ms) base + (length / 500) seconds
    swipe_length = abs(end_x - start_x)
    duration = int(min_duration + (swipe_length / 0.5))

    if debug:
        direction = "→" if start_x < end_x else "←"
        print(f"DEBUG: y={y}, orig=({original_start},{original_end}), final=({start_x},{end_x}) {direction}, len={swipe_length}")

    device.shell(f"input swipe {start_x} {y} {end_x} {y} {duration}")
    time.sleep(delay_ms / 1000.0)  # Delay between swipes

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


def generate_template(output_path):
    """Generate template image showing drawable area with cutoff regions marked"""
    config = load_config()

    # Calculate template dimensions
    screen_width = config['right_x'] - config['left_x']
    screen_height = config['bottom_y'] - config['top_y']
    scale = config['scale']

    width = int(screen_width / scale)
    height = int(screen_height / scale)

    # Create white image (drawable area)
    image = Image.new('L', (width, height), 255)
    pixels = image.load()

    # Mark top-left cutoff region (in template coordinates)
    tl_x = int((config['cutoff_tl_x'] - config['left_x']) / scale)
    tl_y = int((config['cutoff_tl_y'] - config['top_y']) / scale)

    for y in range(min(tl_y, height)):
        for x in range(min(tl_x, width)):
            pixels[x, y] = 128  # Gray for cutoff

    # Mark bottom-right cutoff region
    br_x = int((config['cutoff_br_x'] - config['left_x']) / scale)
    br_y = int((config['cutoff_br_y'] - config['top_y']) / scale)

    for y in range(max(0, br_y), height):
        for x in range(max(0, br_x), width):
            pixels[x, y] = 128  # Gray for cutoff

    # Save template
    image.save(output_path)
    print(f"Template saved to {output_path}")
    print(f"Dimensions: {width}x{height} pixels")
    print(f"Scale: {scale} (1 template pixel = {1/scale:.2f} screen pixels)")
    print(f"White areas: drawable, Gray areas: cutoff regions")


def draw_image(device, image_path, step=1, min_duration=200, delay_ms=25, debug=False):
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

    # Draw the image using swipe gestures with progress bar
    skip = 0
    with tqdm(total=total_swipes, desc="Drawing", unit="swipe") as pbar:
        for i, (start_x, end_x, y) in enumerate(swipe_data, 1):
            if i < skip:
                continue
            screen_x1 = screen_start_x + start_x * scale
            screen_x2 = screen_start_x + end_x * scale
            screen_y = screen_start_y - y * scale  # Subtract y to draw from bottom to top
            swipe(device, int(screen_x1), int(screen_x2), int(screen_y), config, min_duration, delay_ms, debug)
            pbar.update(1)

    print("Drawing completed")

def main():
    parser = argparse.ArgumentParser(description='Draw images on Android device using ADB')
    parser.add_argument('image_path', nargs='?', help='Path to image file')
    parser.add_argument('--step', type=int, default=1,
                       help='Draw every Nth row (default: 1 - all rows)')
    parser.add_argument('--min-duration', type=int, default=200,
                       help='Minimum swipe duration in milliseconds (default: 200)')
    parser.add_argument('--delay', type=int, default=25,
                       help='Delay between swipes in milliseconds (default: 25)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging for swipe directions')
    parser.add_argument('--generate-template', type=str, metavar='OUTPUT',
                       help='Generate template image and save to OUTPUT file')
    args = parser.parse_args()

    # Generate template mode
    if args.generate_template:
        generate_template(args.generate_template)
        return

    # Normal drawing mode
    if not args.image_path:
        parser.error('image_path is required when not generating template')

    device = connect_to_device()
    draw_image(device, args.image_path, step=args.step, min_duration=args.min_duration, delay_ms=args.delay, debug=args.debug)

if __name__ == "__main__":
    main()
