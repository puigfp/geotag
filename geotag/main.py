import argparse
import json
import os
import tempfile

from .exif import get_exif_diff, read_exif, write_exif, parse_exif_timezone_offset
from .location_history import discard_bad_gps_points, read_google_location_history
from .log import log


def add_google_location_to_images(
    location_history_path: str, root_path: str, utc_offset: str
):
    location_history = read_google_location_history(location_history_path)
    location_history = discard_bad_gps_points(location_history)
    timestamps = [loc.timestamp for loc in location_history]
    exif = read_exif(root_path)
    exif_diff = get_exif_diff(exif, location_history, utc_offset)
    with tempfile.TemporaryDirectory() as temp_directory:
        exif_diff_path = os.path.join(temp_directory, "exif_diff.json")
        log.debug(f"writing temporary exif diff json to {exif_diff_path}...")
        with open(exif_diff_path, "w") as f:
            json.dump(exif_diff, f)
        write_exif(root_path, exif_diff_path)


def main():
    parser = argparse.ArgumentParser(
        prog="geotag",
        description="Add GPS metadata to your photos/videos using your Google location history data",
    )
    parser.add_argument(
        "location_history", help="path to your google location history json dump",
    )
    parser.add_argument(
        "root_path", help="path to the photos you want to add GPS info to"
    )
    parser.add_argument(
        "--utc-offset-default",
        help="default UTC time offset of the image creation datetimes, "
        f'only used when the "OffsetTimeOriginal" field is missing from the EXIF '
        '(default value: "+00:00")',
        default="+00:00",
    )
    args = parser.parse_args()

    utc_offset_default = parse_exif_timezone_offset(args.utc_offset_default)
    add_google_location_to_images(
        args.location_history, args.root_path, utc_offset_default
    )
