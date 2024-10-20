import board
import displayio
import gc9a01
import busio
import time
import math
import random
import neopixel

import config  # Import pin configuration

pupil_radius = 40
enable_blink = False

# Frame rate control
target_fps = 40  # Target frame rate (frames per second)
frame_duration = 1.0 / target_fps

# Eye center and initial pupil position
eye_center_x = 120
eye_center_y = 120
pupil_x = eye_center_x
pupil_y = eye_center_y

# Dictionary of "looks" with target positions and speeds
looks = {
    "center": (eye_center_x, eye_center_y, 5),
    "left_fast": (70, eye_center_y, 10),
    "left_slow": (70, eye_center_y, 2),
    "right_fast": (170, eye_center_y, 10),
    "right_slow": (170, eye_center_y, 2),
    "up": (eye_center_x, 70, 5),
    "down": (eye_center_x, 175, 5),
    "up_left": (70, 70, 5),
    "up_right": (170, 70, 5),
    "down_left": (70, 175, 5),
    "down_right": (170, 175, 5)
}

# Palettes for the pupil and sclera (eye whites)
pupil_palettes = {
    "red": 0xFF0000,
    "blue": 0x0000FF,
    "green": 0x00FF00,
    "purple": 0x800080,
    "yellow": 0xFFFF00,
    "orange": 0xFFA500,
    "cyan": 0x00FFFF,
    "pink": 0xFFC0CB
}

sclera_palettes = {
    "white": 0xFFFFFF,
    "light_blue": 0xADD8E6,
    "light_yellow": 0xFFFFE0,
    "light_gray": 0xD3D3D3,
    "lime_green": 0x32CD32,
    "black": 0x000000,
    "purple": 0x800080,
    "pink": 0xFFC0CB
}

if config.ENABLE_WS2812:
    num_pixels = config.WS2812_NUM_PIXELS
    neo_pixel_pin = getattr(board, config.WS2812_PIN)
    pixels = neopixel.NeoPixel(neo_pixel_pin, num_pixels, brightness=0.5, auto_write=False)
    flame_brightness = 0.1

# Release any resources currently in use for the displays
displayio.release_displays()

# Setup SPI bus using pins from config.py
spi = busio.SPI(clock=getattr(board, config.SPI_CLOCK_PIN),
                MOSI=getattr(board, config.SPI_MOSI_PIN))

# Create the display object using pins from config.py
display_bus = displayio.FourWire(
    spi,
    command=getattr(board, config.DISPLAY_DC_PIN),
    chip_select=getattr(board, config.DISPLAY_CS_PIN),
    reset=getattr(board, config.DISPLAY_RST_PIN),
    baudrate=40000000
)

# Set up the display. GC9A01 is a 240x240 display
display = gc9a01.GC9A01(
    display_bus, width=240, height=240, rotation=0
)


def flame_effect():
    global flame_brightness
    flame_yellow = (255, 100, 0)
    flame_orange = (255, 50, 0)
    flame_red = (255, 0, 0)

    # Loop the flame brightness
    flame_brightness += 0.01
    if flame_brightness > 1:
        flame_brightness = 0.0

    # Randomly fill each column with yellow, orange, then red
    for col in range(8):  # Each column in the 8x8 matrix
        # Randomize the starting positions for yellow, orange, and red
        yellow_end = random.randint(1, 2)   # Yellow occupies 1-2 pixels
        orange_end = yellow_end + random.randint(1, 2)  # Orange occupies next 1-2 pixels
        red_start = orange_end  # Remaining pixels will be red

        # Set the colors for the column based on the random positions
        for row in range(8):
            pixel_index = col + row * 8  # Calculate pixel index in the 1D NeoPixel array
            if row < yellow_end:
                pixels[pixel_index] = flame_yellow
            elif row < orange_end:
                pixels[pixel_index] = flame_orange
            else:
                pixels[pixel_index] = flame_red

    # Update brightness
    pixels.brightness = flame_brightness
    pixels.show()


# Function to randomly select a palette for the pupil and sclera
def select_random_palette():
    pupil_color = random.choice(list(pupil_palettes.values()))
    sclera_color = random.choice(list(sclera_palettes.values()))
    return pupil_color, sclera_color

# Initially select a random palette
pupil_color, sclera_color = select_random_palette()

# Create a palette for the pupil
pupil_palette = displayio.Palette(2)
pupil_palette[1] = pupil_color
pupil_palette.make_transparent(0)

# Create a palette for the background (sclera)
background_palette = displayio.Palette(1)
background_palette[0] = sclera_color  # Sclera color

# Fill the background with sclera color
background_bitmap = displayio.Bitmap(240, 240, 1)
background_tilegrid = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)

# Create the pupil bitmap (a smaller circle)
pupil_bitmap = displayio.Bitmap(2 * pupil_radius, 2 * pupil_radius, 1)
for y in range(-pupil_radius, pupil_radius):
    for x in range(-pupil_radius, pupil_radius):
        if x * x + y * y <= pupil_radius * pupil_radius:
            pupil_bitmap[x + pupil_radius, y + pupil_radius] = 1

# Create a TileGrid for the pupil
pupil_tilegrid = displayio.TileGrid(pupil_bitmap, pixel_shader=pupil_palette, x=100, y=100)

# Create a group and add the TileGrids
group = displayio.Group()
group.append(background_tilegrid)
group.append(pupil_tilegrid)

# Set the root group to display
display.root_group = group

# Function to move the pupil towards a target position
def move_pupil_to_target(target_x, target_y, speed):
    global pupil_x, pupil_y
    # Calculate the distance to the target
    dx = target_x - pupil_x
    dy = target_y - pupil_y
    distance = math.sqrt(dx**2 + dy**2)

    # If the distance is less than the speed, snap to the target
    if distance < speed:
        pupil_x = target_x
        pupil_y = target_y
    else:
        # Move towards the target at the given speed
        move_x = (dx / distance) * speed
        move_y = (dy / distance) * speed
        pupil_x += move_x
        pupil_y += move_y

# Current target
current_look = "center"
last_change_time = time.monotonic()
change_interval = 2  # Change the look every 2 seconds
palette_change_interval = 5  # Change palette every 5 seconds
last_palette_change_time = time.monotonic()

# Animate the pupil movement
while True:
    start_time = time.monotonic()

    if config.ENABLE_WS2812:
        flame_effect()

    # Check if it's time to change the palette
    if time.monotonic() - last_palette_change_time > palette_change_interval:
        pupil_color, sclera_color = select_random_palette()
        pupil_palette[1] = pupil_color
        background_palette[0] = sclera_color
        last_palette_change_time = time.monotonic()

    # Check if it's time to change the look
    if time.monotonic() - last_change_time > change_interval:
        # Pick a random look from the dictionary
        current_look = random.choice(list(looks.keys()))
        last_change_time = time.monotonic()  # Reset the change time

    # Get the target position and speed for the current look
    target_x, target_y, speed = looks[current_look]

    # Move the pupil towards the target position
    move_pupil_to_target(target_x, target_y, speed)

    # Update the pupil's position on the screen
    pupil_tilegrid.x = int(pupil_x) - pupil_radius
    pupil_tilegrid.y = int(pupil_y) - pupil_radius

    # Calculate how long to sleep to maintain the target frame rate
    elapsed_time = time.monotonic() - start_time
    sleep_time = max(0, frame_duration - elapsed_time)
    time.sleep(sleep_time)