import board
import displayio
import gc9a01
import busio
import time
import math

import config  # Import pin configuration

pupil_radius = 35
pupil_color = 0xF28C28  # orange
sclera_color = 0xFFFFFF  # white


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
    baudrate=24000000
)

# Set up the display. GC9A01 is a 240x240 display
display = gc9a01.GC9A01(
    display_bus, width=240, height=240, rotation=0
)

# Create a palette for the pupil
palette = displayio.Palette(2)
palette[0] = sclera_color  # White for the eye
palette[1] = pupil_color  # Orange for the pupil

# Fill the background with white
background_bitmap = displayio.Bitmap(240, 240, 1)
background_palette = displayio.Palette(1)
background_palette[0] = 0xFFFFFF  # White background

# Create a TileGrid for the background
background_tilegrid = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)

# Create the pupil bitmap (a smaller circle)
pupil_bitmap = displayio.Bitmap(2 * pupil_radius, 2 * pupil_radius, 1)

for y in range(-pupil_radius, pupil_radius):
    for x in range(-pupil_radius, pupil_radius):
        if x * x + y * y <= pupil_radius * pupil_radius:
            pupil_bitmap[x + pupil_radius, y + pupil_radius] = 1

# Create a TileGrid for the pupil
pupil_tilegrid = displayio.TileGrid(pupil_bitmap, pixel_shader=palette, x=100, y=100)

# Create a group and add the TileGrids
group = displayio.Group()
group.append(background_tilegrid)
group.append(pupil_tilegrid)

# Set the root group to display
display.root_group = group

# Frame rate control
target_fps = 40  # Target frame rate (frames per second)
frame_duration = 1.0 / target_fps

# Animate the pupil movement
eye_center_x = 120
eye_center_y = 120
angle = 0
distance = 50  # Distance from the center of the eye
while True:
    start_time = time.monotonic()

    # Calculate the new position for the pupil
    pupil_x = int(eye_center_x + distance * math.cos(angle)) - pupil_radius
    pupil_y = int(eye_center_y + distance * math.sin(angle)) - pupil_radius

    # Update the pupil's position
    pupil_tilegrid.x = pupil_x
    pupil_tilegrid.y = pupil_y

    # Increment the angle for circular motion
    angle += 0.1
    if angle >= 2 * math.pi:
        angle = 0

    # Calculate how long to sleep to maintain the target frame rate
    elapsed_time = time.monotonic() - start_time
    sleep_time = max(0, frame_duration - elapsed_time)
    time.sleep(sleep_time)