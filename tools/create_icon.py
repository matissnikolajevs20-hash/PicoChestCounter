import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main(output_path):
    image = Image.new("RGBA", (256, 256), (17, 24, 32, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 244, 244), radius=52, fill=(27, 39, 50, 255))
    draw.polygon(
        [(128, 34), (214, 174), (42, 174)],
        fill=(242, 193, 78, 255),
    )
    draw.polygon(
        [(128, 73), (177, 154), (79, 154)],
        fill=(27, 39, 50, 255),
    )
    draw.rounded_rectangle((63, 165, 193, 218), radius=9, fill=(115, 210, 160, 255))
    draw.rectangle((63, 179, 193, 190), fill=(52, 140, 105, 255))
    draw.rounded_rectangle((117, 184, 139, 199), radius=4, fill=(242, 193, 78, 255))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_icon.py OUTPUT.ico")
    main(sys.argv[1])
