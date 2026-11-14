"""Transforme une photo portrait en photo paysage 16:9 sans bandes noires.

La photo d'origine est placée, entière, au centre d'un arrière-plan
construit à partir d'elle-même : zoomée pour remplir le 16:9, puis floutée.

Exemples :
    python portrait_to_landscape.py photo.jpg
    python portrait_to_landscape.py photos/ --output-dir sortie
    python portrait_to_landscape.py photo.jpg --width 3840 --height 2160
    python portrait_to_landscape.py photo.jpg --feather 0
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_BLUR_RADIUS = 40
DEFAULT_FEATHER = 0  # largeur en pixels du fondu sur les bords de la photo
BACKGROUND_BRIGHTNESS = 0.8  # < 1 assombrit le fond pour faire ressortir la photo
JPEG_QUALITY = 95
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def load_photo(path: Path) -> Image.Image:
    """Ouvre la photo en respectant son orientation EXIF (photos de téléphone)."""
    with Image.open(path) as image:
        upright_image = ImageOps.exif_transpose(image)
        return upright_image.convert("RGB")


def is_portrait(photo: Image.Image) -> bool:
    """Vrai si la photo est plus haute que large."""
    return photo.height > photo.width


def make_blurred_background(photo: Image.Image, size: tuple[int, int], blur_radius: int) -> Image.Image:
    """Zoome sur le centre de la photo pour remplir `size`, puis la floute."""
    zoomed = ImageOps.fit(photo, size, method=Image.Resampling.LANCZOS)
    blurred = zoomed.filter(ImageFilter.GaussianBlur(blur_radius))
    return ImageEnhance.Brightness(blurred).enhance(BACKGROUND_BRIGHTNESS)


def make_feather_mask(size: tuple[int, int], feather: int) -> Image.Image:
    """Masque opaque au centre qui devient transparent sur les `feather` pixels
    des bords gauche et droit (le haut et le bas restent nets)."""
    width, height = size
    mask = Image.new("L", size, color=0)
    opaque_area = (feather, 0, width - 1 - feather, height - 1)
    ImageDraw.Draw(mask).rectangle(opaque_area, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(feather / 2))


def paste_centered(background: Image.Image, photo: Image.Image, feather: int) -> Image.Image:
    """Réduit la photo pour qu'elle tienne entière dans le fond, et la colle au centre
    avec des bords adoucis pour qu'elle se fonde dans l'arrière-plan."""
    fitted_photo = ImageOps.contain(photo, background.size, method=Image.Resampling.LANCZOS)
    feather_mask = make_feather_mask(fitted_photo.size, feather)

    left = (background.width - fitted_photo.width) // 2
    top = (background.height - fitted_photo.height) // 2

    result = background.copy()
    result.paste(fitted_photo, (left, top), mask=feather_mask)
    return result


def portrait_to_landscape(photo: Image.Image, size: tuple[int, int], blur_radius: int, feather: int) -> Image.Image:
    """Construit l'image paysage : fond flouté + photo entière au centre."""
    background = make_blurred_background(photo, size, blur_radius)
    return paste_centered(background, photo, feather)


def find_photos(inputs: list[Path]) -> list[Path]:
    """Liste les photos à traiter : fichiers donnés directement ou contenus dans un dossier."""
    photos = []
    for path in inputs:
        if path.is_dir():
            photos.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS))
        else:
            photos.append(path)
    return photos


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transforme des photos portrait en photos paysage 16:9 avec un fond flouté."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Photos ou dossiers de photos à traiter.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Dossier de sortie (défaut : output).")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help=f"Largeur de sortie (défaut : {DEFAULT_WIDTH}).")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help=f"Hauteur de sortie (défaut : {DEFAULT_HEIGHT}).")
    parser.add_argument("--blur", type=int, default=DEFAULT_BLUR_RADIUS, help=f"Intensité du flou (défaut : {DEFAULT_BLUR_RADIUS}).")
    parser.add_argument("--feather", type=int, default=DEFAULT_FEATHER, help=f"Fondu des bords de la photo en pixels, 0 pour désactiver (défaut : {DEFAULT_FEATHER}).")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    output_size = (args.width, args.height)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for photo_path in find_photos(args.inputs):
        photo = load_photo(photo_path)
        if not is_portrait(photo):
            print(f"{photo_path} : ignorée (pas en portrait)")
            continue

        landscape = portrait_to_landscape(photo, output_size, args.blur, args.feather)

        output_path = args.output_dir / f"{photo_path.stem}_16x9.jpg"
        landscape.save(output_path, quality=JPEG_QUALITY)
        print(f"{photo_path} -> {output_path}")


if __name__ == "__main__":
    main()
