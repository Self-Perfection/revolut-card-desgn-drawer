# Revolut Card Custom Design Drawing Tool

A tool for drawing custom designs on Revolut cards using Android Debug Bridge (ADB). The tool uses swipe gestures to replicate images pixel-by-pixel on your Android device screen, allowing you to create personalized card designs.

## Requirements

- **Python 3.8+**
- **ADB (Android Debug Bridge)** - Must be installed and accessible in PATH
- **Android device** with USB debugging enabled and connected via USB or wireless ADB

## Installation

### 1. Install Dependencies

**Option A: Using uv (recommended)**

[uv](https://github.com/astral-sh/uv) automatically manages dependencies when you run scripts with `uv run`:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

No additional dependency installation needed - `uv run` handles everything automatically.

**Option B: Using plain Python**

If you prefer to use plain `python`, install dependencies manually:

```bash
pip install pure-python-adb numpy Pillow
```

Then you can run scripts with `python` instead of `uv run` throughout this guide.

### 2. Set up ADB

Install ADB for your platform:
- **macOS**: `brew install android-platform-tools`
- **Linux**: `sudo apt install adb` or `sudo pacman -S android-tools`
- **Windows**: Download [Platform Tools](https://developer.android.com/studio/releases/platform-tools)

Enable USB debugging on your Android device (Settings → Developer Options → USB Debugging).

### 3. Connect your device

```bash
# Check device is connected
adb devices
```

You should see your device listed.

## Configuration

The tool uses a two-tier configuration system:

- **config.default.toml** - Default configuration with reasonable bounds for typical devices
- **config.toml** - Optional user configuration that overrides defaults

**The default configuration is acceptable for most use cases.** You only need to calibrate if:
- Your device has a different screen size/resolution
- The card is positioned differently
- The default bounds don't align with your drawable area

### Configuration Parameters

```toml
[bounds]
left_x = 85      # Left boundary of main drawing rectangle
right_x = 990    # Right boundary
top_y = 649      # Top boundary
bottom_y = 1388  # Bottom boundary

[cutoff_top_left]
x = 274          # Top-left corner cutoff x-coordinate
y = 800          # Top-left corner cutoff y-coordinate

[cutoff_bottom_right]
x = 660          # Bottom-right corner cutoff x-coordinate
y = 1110         # Bottom-right corner cutoff y-coordinate

[settings]
scale = 0.4      # Template image scaling factor
```

## Template Image

The repository includes `template.png` which visually shows the drawable area:

- **White areas**: Drawable region where your design will appear
- **Gray areas**: Cutoff corner regions that are excluded from drawing

Use this template as a guide when creating your custom design image.

### Regenerating the Template

If you modify the configuration (either `config.default.toml` or create a `config.toml`), you can regenerate the template:

```bash
# With uv
uv run main.py --generate-template template.png

# Or with plain python
python main.py --generate-template template.png
```

The template dimensions are scaled according to the `scale` parameter in your configuration. A scale of 0.4 means 1 template pixel = 2.5 screen pixels.

## Calibration (Optional)

If you need to calibrate the drawing area for your specific device or card placement:

```bash
# With uv
uv run calibrate.py

# Or with plain python
python calibrate.py
```

The calibration process uses an interactive binary search method:
1. Draws test lines on your device
2. Asks if the line is visible inside the drawable area
3. Narrows down the precise boundaries using binary search (1-pixel precision)
4. Saves the calibrated configuration to `config.toml`

**Controls during calibration:**
- `y` - Line is visible inside the drawable area
- `n` - Line is not visible (outside bounds)
- `r` - Repeat the current test (redraw line)
- `s` - Start over from the beginning of current boundary

The process calibrates:
1. Main rectangle boundaries (left, right, top, bottom)
2. Corner cutoff regions (if present)

## Usage

### Basic Drawing

```bash
# With uv
uv run main.py your_design.png

# Or with plain python
python main.py your_design.png
```

### Faster Drawing (Lower Resolution)

Draw every Nth row for faster rendering:

```bash
# Draw every 2nd row (50% faster, slightly lower quality)
uv run main.py your_design.png --step 2
# or: python main.py your_design.png --step 2

# Draw every 3rd row (66% faster, lower quality)
uv run main.py your_design.png --step 3
# or: python main.py your_design.png --step 3
```

### Image Preparation Tips

- **Format**: Any common format (PNG, JPG, etc.)
- **Color**: Will be converted to grayscale and binarized (threshold at 128)
- **Dimensions**: Should match template dimensions for best results
- **Black pixels**: Will be drawn (white pixels are skipped)

## Workflow

1. **Prepare your design**
   - Create an image matching the template dimensions
   - Use the template as a guide (white = drawable area)

2. **(Optional) Calibrate**
   - Run calibration if defaults don't work for your setup
   - This creates `config.toml` with your custom bounds

3. **(Optional) Regenerate template**
   - Regenerate the template after calibration
   - Use the new template as a guide for your design

4. **Draw on device**
   - Ensure your Android device is connected via ADB
   - Open the Revolut app to the card customization screen
   - Run the drawing script with your design image

## Examples

```bash
# Generate a new template after configuration changes
uv run main.py --generate-template my_template.png

# Draw a design with full resolution
uv run main.py cross.png

# Draw a design quickly with lower resolution
uv run main.py my_logo.png --step 2
```

## How It Works

The tool works by:
1. Loading your design image and converting it to binary (black/white)
2. Extracting continuous horizontal segments of black pixels
3. Mapping image coordinates to screen coordinates using the configuration
4. Executing ADB swipe gestures to "draw" each segment on the device
5. Respecting boundary constraints and cutoff regions to avoid drawing outside the valid area

Each row of black pixels becomes a series of horizontal swipe gestures that replicate the design on your device screen.

## Troubleshooting

**Device not found:**
- Run `adb devices` to verify connection
- Enable USB debugging in Developer Options
- Try `adb kill-server && adb start-server`

**Drawing is misaligned:**
- Run calibration: `uv run calibrate.py`
- Ensure card is positioned consistently on screen
- Check that screen resolution matches expectations

**Drawing is incomplete:**
- Verify your design fits within the template bounds (white area)
- Check that cutoff regions are configured correctly
- Try reducing `--step` value for more complete rendering

## License

This is a personal tool for customizing Revolut cards. Use responsibly and in accordance with Revolut's terms of service.
