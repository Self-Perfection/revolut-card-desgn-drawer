from ppadb.client import Client as AdbClient
import numpy as np
import time
from PIL import Image
import sys

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

def swipe(device, start_x, end_x, y):
    duration = 1000
    end_y = y  # Swipe vertically
    if start_x >= 610 and end_y >= 1100:
        return
    if start_x >= 940:
        return
    if end_x >= 610 and end_y >= 1100:
        end_x = 610
    if start_x <= 300 and y <= 800:
        start_x = 300
    if y <= 680:
        return
    device.shell(f"input swipe {start_x} {y} {end_x} {end_y} {duration}")
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

def draw_image(device, image_path):
    # Load and process the image
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    image_array = np.array(image)
    image_array = (image_array < 128).astype(np.uint8) * 255  # Binarize the image

    # Extract swipe data
    swipe_data = extract_continuous_swipes(image_array)


    # Map image coordinates to screen coordinates
    screen_start_x, screen_start_y = 180, 1280  # Starting point at bottom left
    scale = 0.4  # Scaling factors

    total_swipes = len(swipe_data)
    print(f"Total swipes to perform: {total_swipes}")
    skip = 0
    # Draw the image using swipe gestures
    for i, (start_x, end_x, y) in enumerate(swipe_data, 1):
        if i < skip:
            continue
        screen_x1 = screen_start_x + start_x * scale
        screen_x2 = screen_start_x + end_x * scale
        screen_y = screen_start_y - y * scale  # Subtract y to draw from bottom to top
        swipe(device, int(screen_x1), int(screen_x2), int(screen_y))
        
        # Log progress
        if i % 10 == 0 or i == total_swipes:
            progress = (i / total_swipes) * 100
            print(f"Progress: {progress:.2f}% ({i}/{total_swipes} swipes)")

    print("Drawing completed")

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    device = connect_to_device()
    draw_image(device, image_path)

if __name__ == "__main__":
    main()
