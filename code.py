import board
import displayio
import gc9a01
import busio
import config

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

# Create a simple bitmap to test the display
bitmap = displayio.Bitmap(240, 240, 1)
palette = displayio.Palette(1)
palette[0] = 0xFF0000  # Red color

# Create a TileGrid to hold the bitmap
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# Create a Group to hold the TileGrid
group = displayio.Group()
group.append(tile_grid)

# Set the root group to show the content
display.root_group = group

# Keep the display on
while True:
    pass