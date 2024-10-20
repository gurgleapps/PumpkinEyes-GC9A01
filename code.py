import board
import displayio
import gc9a01
import busio
import time
import math
import random

import config  # Import pin configuration

pupil_radius = 40
pupil_color = 0xFF0000
sclera_color = 0xFFFFFF  # white
eyelid_color = 0xF28C28  # orange
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

# Create a palette for the pupil
pupil_palette = displayio.Palette(2)
pupil_palette[1] = pupil_color
pupil_palette.make_transparent(0)


palette = displayio.Palette(2)
palette[0] = sclera_color  # White for the eye
palette[1] = pupil_color   # Orange for the pupil

# Fill the background with white
background_bitmap = displayio.Bitmap(240, 240, 1)
background_palette = displayio.Palette(1)
background_palette[0] = sclera_color  # White background

# Create a TileGrid for the background
background_tilegrid = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)

# Create the top eyelid
eyelid_palette = displayio.Palette(2)
eyelid_palette[1] = eyelid_color
top_eyelid_bitmap = displayio.Bitmap(240, 120, 1)
top_eyelid_bitmap.fill(1)
top_eyelid_tilegrid = displayio.TileGrid(top_eyelid_bitmap, pixel_shader=eyelid_palette)

# Create the bottom eyelid
bottom_eyelid_bitmap = displayio.Bitmap(240, 120, 1)
bottom_eyelid_bitmap.fill(1)
bottom_eyelid_tilegrid = displayio.TileGrid(bottom_eyelid_bitmap, pixel_shader=eyelid_palette, y=120)

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
if enable_blink:
    group.append(top_eyelid_tilegrid)
    group.append(bottom_eyelid_tilegrid)
        # Blinking variables
    blink_offset = 0
    blinking = False
    blink_direction = 1  # 1 for closing, -1 for opening
    next_blink_time = time.monotonic() + random.uniform(5, 15)

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

# Animate the pupil movement
while True:
    start_time = time.monotonic()

    # Handle blinking
    if enable_blink and time.monotonic() >= next_blink_time and not blinking:
        blink_offset = 0
        blink_direction = 1
        blinking = True

    if enable_blink and blinking:
        blink_offset += blink_direction * 60

        if blink_offset >= 120:  # Fully closed
            blink_direction = -1  # Start opening
        elif blink_offset <= 0:  # Fully open
            blink_direction = 1  # Start closing again later
            blinking = False
            next_blink_time = time.monotonic() + random.uniform(2, 5)  # Randomize next blink time

        top_eyelid_tilegrid.y = -120 + blink_offset
        bottom_eyelid_tilegrid.y = 240 - blink_offset


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