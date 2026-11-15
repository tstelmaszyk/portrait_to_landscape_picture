# portrait_to_landscape

Command-line tool that converts portrait photos into 16:9 landscape images for
video editing. Instead of black bars on the sides, the photo is placed whole in
the center of a blurred, zoomed-in copy of itself.

```
+--------------------------------------+
|  blurred  |               |  blurred |
|  zoomed   |  original     |  zoomed  |
|  copy     |  photo        |  copy    |
|           |  (uncropped)  |          |
+--------------------------------------+
```

## Requirements

- Python 3.10+
- Pillow 10.1+

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python portrait_to_landscape.py <photo-or-directory> [<photo-or-directory> ...] [options]
```

Examples:

```bash
python portrait_to_landscape.py photo.jpg
python portrait_to_landscape.py photos/ --output-dir out
python portrait_to_landscape.py photo.jpg --width 3840 --height 2160
python portrait_to_landscape.py photos/ --blur 60 --feather 15
```

Options:

| Option         | Default  | Description                                                     |
| -------------- | -------- | --------------------------------------------------------------- |
| `--output-dir` | `output` | Output directory, created if missing.                           |
| `--width`      | `1920`   | Output width in pixels.                                         |
| `--height`     | `1080`   | Output height in pixels.                                        |
| `--blur`       | `40`     | Gaussian blur radius applied to the background.                 |
| `--feather`    | `0`      | Width in pixels of the fade on the left and right photo edges.  |

Output files are written as JPEG, named `<input-name>_16x9.jpg`.

Behavior:

- Directories are scanned non-recursively for `.jpg`, `.jpeg`, `.png`, `.webp`,
  `.bmp`, `.tif` and `.tiff` files.
- Only portrait photos (height > width) are converted. Landscape and square
  photos are skipped and reported on stdout.
- EXIF orientation is applied before anything else, so phone photos stored
  sideways are handled correctly.
- HEIC files are not supported (Pillow has no native HEIC decoder).

## Architecture

Everything lives in `portrait_to_landscape.py`. The processing pipeline for a
single photo is:

```
load_photo -> is_portrait -> portrait_to_landscape
                               |-- make_blurred_background
                               `-- paste_centered
                                     `-- make_feather_mask
```

| Function                  | Role                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------- |
| `load_photo`              | Opens the file, applies EXIF orientation, converts to RGB.                            |
| `is_portrait`             | Filters out photos that are not taller than wide.                                     |
| `make_blurred_background` | Center-crops and scales the photo to the output size (`ImageOps.fit`), blurs and darkens it. |
| `paste_centered`          | Scales the photo to fit inside the output frame (`ImageOps.contain`) and pastes it in the center. |
| `make_feather_mask`       | Builds the alpha mask used for the paste; a blurred rectangle inset on the left and right edges. |
| `portrait_to_landscape`   | Combines the two steps above.                                                         |
| `find_photos`             | Expands the CLI inputs (files and directories) into a list of photo paths.            |
| `parse_arguments`, `main` | CLI entry point.                                                                      |

Tunable values that are not exposed on the command line are defined as
constants at the top of the file: `BACKGROUND_BRIGHTNESS` (background
darkening factor), `JPEG_QUALITY` and `SUPPORTED_EXTENSIONS`.
