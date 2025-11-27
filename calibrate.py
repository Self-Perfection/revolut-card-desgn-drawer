# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pure-python-adb>=0.3.0.dev0",
# ]
# ///

import sys
import time
import re
import tty
import termios
from config import load_config, connect_to_device


def getch():
    """Read a single character from stdin without requiring Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def draw_vertical_line(device, x, y_start, y_end):
    """Draws a vertical line using two swipes from center"""
    mid_y = (y_start + y_end) // 2
    # Swipe from center up
    device.shell(f"input swipe {x} {mid_y} {x} {y_start} 500")
    time.sleep(0.1)
    # Swipe from center down
    device.shell(f"input swipe {x} {mid_y} {x} {y_end} 500")


def draw_horizontal_line(device, y, x_start, x_end):
    """Draws a horizontal line using two swipes from center"""
    mid_x = (x_start + x_end) // 2
    # Swipe from center left
    device.shell(f"input swipe {mid_x} {y} {x_start} {y} 500")
    time.sleep(0.1)
    # Swipe from center right
    device.shell(f"input swipe {mid_x} {y} {x_end} {y} 500")


def calibrate_boundary(device, name, min_val, max_val, is_horizontal, defaults):
    """
    Calibrate a boundary using binary search (1px precision)
    """
    restart = True
    while restart:
        restart = False
        low = max(0, min_val)  # Don't allow negative coordinates
        high = max_val

        print(f"\n=== Calibrating {name} ===")
        print(f"Search range: {low} to {high}")

        while high - low > 1:  # 1 pixel precision
            mid = (low + high) // 2

            repeat = True
            while repeat:
                repeat = False

                # Draw test line automatically
                print(f"Drawing test line at {name}={mid}...")

                if is_horizontal:
                    # Horizontal line: draw from left to right using defaults
                    draw_horizontal_line(device, mid, defaults['left_x'], defaults['right_x'])
                else:
                    # Vertical line: draw from top to bottom using defaults
                    draw_vertical_line(device, mid, defaults['top_y'], defaults['bottom_y'])

                # Ask user
                while True:
                    print(f"Visible inside? (y/n/r=repeat/s=start over): ", end='', flush=True)
                    answer = getch().lower()
                    print(answer)  # Echo the character

                    if answer in ['y', 'n', 'r', 's']:
                        break
                    print("Please answer 'y', 'n', 'r', or 's'")

                if answer == 'r':
                    repeat = True
                elif answer == 's':
                    restart = True
                    break

            if restart:
                break

            if answer == 'y':
                # Line is visible - boundary is further
                if name in ['left_x', 'top_y', 'cutoff_tl_x', 'cutoff_tl_y']:
                    high = mid  # Shift left/up
                else:
                    low = mid   # Shift right/down
            elif answer == 'n':
                # Line is not visible - boundary is closer
                if name in ['left_x', 'top_y', 'cutoff_tl_x', 'cutoff_tl_y']:
                    low = mid   # Shift right/down
                else:
                    high = mid  # Shift left/up

            print(f"Range narrowed to: {low} - {high}")

    result = (low + high) // 2
    print(f"✓ {name} = {result}")
    return result


def save_config(bounds):
    """Save configuration to config.toml"""
    toml_content = f"""# Drawing area configuration
# Main rectangle bounds
[bounds]
left_x = {bounds['left_x']}
right_x = {bounds['right_x']}
top_y = {bounds['top_y']}
bottom_y = {bounds['bottom_y']}

# Cutoff regions (excluded corners)
[cutoff_top_left]
x = {bounds['cutoff_tl_x']}
y = {bounds['cutoff_tl_y']}

[cutoff_bottom_right]
x = {bounds['cutoff_br_x']}
y = {bounds['cutoff_br_y']}

[settings]
scale = 0.4
"""
    with open('config.toml', 'w') as f:
        f.write(toml_content)

    print("\n✓ Configuration saved to config.toml")
    print(f"Main bounds: left={bounds['left_x']}, right={bounds['right_x']}, "
          f"top={bounds['top_y']}, bottom={bounds['bottom_y']}")
    print(f"Top-left cutoff: x={bounds['cutoff_tl_x']}, y={bounds['cutoff_tl_y']}")
    print(f"Bottom-right cutoff: x={bounds['cutoff_br_x']}, y={bounds['cutoff_br_y']}")


def main():
    device = connect_to_device()

    print("=== Binary Search Boundary Calibration ===")
    print("Options: y=inside, n=outside, r=repeat, s=start over\n")

    # Load defaults for drawing test lines
    defaults = load_config()
    print(f"Loaded defaults from config.default.toml")
    print(f"  Drawing area: [{defaults['left_x']}, {defaults['right_x']}] x [{defaults['top_y']}, {defaults['bottom_y']}]\n")

    # Get screen size
    size_output = device.shell("wm size")
    match = re.search(r'(\d+)x(\d+)', size_output)
    if match:
        screen_width = int(match.group(1))
        screen_height = int(match.group(2))
    else:
        screen_width, screen_height = 1080, 2400  # Fallback

    print(f"Screen size detected: {screen_width}x{screen_height}\n")

    bounds = {}

    # Stage 1: Calibrate main 4 rectangle boundaries
    print("=== STAGE 1: Main Rectangle Boundaries ===\n")

    bounds['left_x'] = calibrate_boundary(device, "left_x", 0, screen_width//2,
                                         False, defaults)
    bounds['right_x'] = calibrate_boundary(device, "right_x", screen_width//2, screen_width,
                                          False, defaults)
    bounds['top_y'] = calibrate_boundary(device, "top_y", 0, screen_height//2,
                                        True, defaults)
    bounds['bottom_y'] = calibrate_boundary(device, "bottom_y", screen_height//2, screen_height,
                                           True, defaults)

    print(f"\n✓ Main rectangle: [{bounds['left_x']}, {bounds['right_x']}] x [{bounds['top_y']}, {bounds['bottom_y']}]\n")

    # Stage 2: Ask about corner cutoffs
    print("=== STAGE 2: Corner Cutoffs ===\n")

    tl_cutoff = input("Is top-left corner cut off? (y/n): ").strip().lower() == 'y'
    br_cutoff = input("Is bottom-right corner cut off? (y/n): ").strip().lower() == 'y'

    # Stage 3: Calibrate cutoffs if they exist
    # Update defaults with newly calibrated main bounds for better test line drawing
    defaults['left_x'] = bounds['left_x']
    defaults['right_x'] = bounds['right_x']
    defaults['top_y'] = bounds['top_y']
    defaults['bottom_y'] = bounds['bottom_y']

    if tl_cutoff:
        print("\n=== STAGE 3a: Top-Left Corner Cutoff ===")
        bounds['cutoff_tl_x'] = calibrate_boundary(device, "cutoff_tl_x",
                                                   bounds['left_x'],
                                                   (bounds['left_x'] + bounds['right_x'])//2,
                                                   False, defaults)
        bounds['cutoff_tl_y'] = calibrate_boundary(device, "cutoff_tl_y",
                                                   bounds['top_y'],
                                                   (bounds['top_y'] + bounds['bottom_y'])//2,
                                                   True, defaults)
    else:
        # No cutoff - set boundaries to rectangle edges
        bounds['cutoff_tl_x'] = bounds['left_x']
        bounds['cutoff_tl_y'] = bounds['top_y']

    if br_cutoff:
        print("\n=== STAGE 3b: Bottom-Right Corner Cutoff ===")
        bounds['cutoff_br_x'] = calibrate_boundary(device, "cutoff_br_x",
                                                   (bounds['left_x'] + bounds['right_x'])//2,
                                                   bounds['right_x'],
                                                   False, defaults)
        bounds['cutoff_br_y'] = calibrate_boundary(device, "cutoff_br_y",
                                                   (bounds['top_y'] + bounds['bottom_y'])//2,
                                                   bounds['bottom_y'],
                                                   True, defaults)
    else:
        # No cutoff - set boundaries to rectangle edges
        bounds['cutoff_br_x'] = bounds['right_x']
        bounds['cutoff_br_y'] = bounds['bottom_y']

    save_config(bounds)


if __name__ == "__main__":
    main()
