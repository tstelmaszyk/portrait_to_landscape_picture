"""Convert a portrait photo into a 16:9 landscape image without black bars.

The original photo is placed, uncropped, in the center of a background
built from the photo itself: zoomed in to fill the 16:9 frame, then blurred.

Examples:
    python portrait_to_landscape.py photo.jpg
    python portrait_to_landscape.py photos/ --output-dir out
    python portrait_to_landscape.py photo.jpg --width 3840 --height 2160
    python portrait_to_landscape.py photo.jpg --feather 15
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_BLUR_RADIUS = 40
DEFAULT_FEATHER = 0  # width in pixels of the fade on the photo edges
BACKGROUND_BRIGHTNESS = 0.8  # < 1 darkens the background so the photo stands out
JPEG_QUALITY = 95
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def load_photo(path: Path) -> Image.Image:
    """Open the photo and apply its EXIF orientation (phone photos)."""
    with Image.open(path) as image:
        upright_image = ImageOps.exif_transpose(image)
        return upright_image.convert("RGB")


def is_portrait(photo: Image.Image) -> bool:
    """Return True if the photo is taller than it is wide."""
    return photo.height > photo.width


def make_blurred_background(photo: Image.Image, size: tuple[int, int], blur_radius: int) -> Image.Image:
    """Zoom in on the center of the photo to fill `size`, then blur it."""
    zoomed = ImageOps.fit(photo, size, method=Image.Resampling.LANCZOS)
    blurred = zoomed.filter(ImageFilter.GaussianBlur(blur_radius))
    return ImageEnhance.Brightness(blurred).enhance(BACKGROUND_BRIGHTNESS)


def make_feather_mask(size: tuple[int, int], feather: int) -> Image.Image:
    """Mask that is opaque in the center and fades to transparent over the last
    `feather` pixels of the left and right edges (top and bottom stay sharp)."""
    width, height = size
    mask = Image.new("L", size, color=0)
    opaque_area = (feather, 0, width - 1 - feather, height - 1)
    ImageDraw.Draw(mask).rectangle(opaque_area, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather / 2))


def paste_centered(background: Image.Image, photo: Image.Image, feather: int) -> Image.Image:
    """Shrink the photo so it fits entirely in the background and paste it in the
    center, with softened edges so it blends into the background."""
    fitted_photo = ImageOps.contain(photo, background.size, method=Image.Resampling.LANCZOS)
    feather_mask = make_feather_mask(fitted_photo.size, feather)

    left = (background.width - fitted_photo.width) // 2
    top = (background.height - fitted_photo.height) // 2

    result = background.copy()
    result.paste(fitted_photo, (left, top), mask=feather_mask)
    return result


def portrait_to_landscape(photo: Image.Image, size: tuple[int, int], blur_radius: int, feather: int) -> Image.Image:
    """Build the landscape image: blurred background + whole photo in the center."""
    background = make_blurred_background(photo, size, blur_radius)
    return paste_centered(background, photo, feather)


def find_photos(inputs: list[Path]) -> list[Path]:
    """List the photos to process: files given directly or contained in a directory."""
    photos = []
    for path in inputs:
        if path.is_dir():
            photos.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS))
        else:
            photos.append(path)
    return photos


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert portrait photos into 16:9 landscape images with a blurred background."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Photos or directories of photos to process.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Output directory (default: output).")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help=f"Output width (default: {DEFAULT_WIDTH}).")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help=f"Output height (default: {DEFAULT_HEIGHT}).")
    parser.add_argument("--blur", type=int, default=DEFAULT_BLUR_RADIUS, help=f"Background blur radius (default: {DEFAULT_BLUR_RADIUS}).")
    parser.add_argument("--feather", type=int, default=DEFAULT_FEATHER, help=f"Width in pixels of the fade on the photo edges, 0 to disable (default: {DEFAULT_FEATHER}).")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    output_size = (args.width, args.height)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for photo_path in find_photos(args.inputs):
        photo = load_photo(photo_path)
        if not is_portrait(photo):
            print(f"{photo_path}: skipped (not portrait)")
            continue

        landscape = portrait_to_landscape(photo, output_size, args.blur, args.feather)

        output_path = args.output_dir / f"{photo_path.stem}_16x9.jpg"
        landscape.save(output_path, quality=JPEG_QUALITY)
        print(f"{photo_path} -> {output_path}")


if __name__ == "__main__":
    main()
