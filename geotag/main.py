import argparse
import json
import os
import tempfile

from .exif import get_exif_diff, read_exif, write_exif
from .gps import discard_bad_gps_points, read_google_location_history
from .log import log


def add_google_location_to_images(
    location_history_path: str, root_path: str, utc_offset: float
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
        "--utc-offset",
        help="photos creation datetime offset (in hours) with UTC time (default: 0.0 hours)",
        type=float,
        default=0.0,
    )
    args = parser.parse_args()
    add_google_location_to_images(
        args.location_history, args.root_path, args.utc_offset
    )
