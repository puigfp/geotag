import argparse
import json
import os
import tempfile

from .exif import (
    get_exif_diff,
    merge_sidecar_exif,
    parse_exif_timezone_offset,
    read_exif,
    write_exif,
)
from .location_history import discard_bad_gps_points, read_google_location_history
from .log import log


def add_google_location_to_images(
    location_history_path: str, root_path: str, utc_offset: str, use_sidecar: bool
):
    location_history = read_google_location_history(location_history_path)
    location_history = discard_bad_gps_points(location_history)
    all_exif = read_exif(root_path)
    exif = merge_sidecar_exif(all_exif)
    exif_diff = get_exif_diff(exif, location_history, utc_offset, use_sidecar)
    with tempfile.TemporaryDirectory() as temp_directory:
        exif_diff_path = os.path.join(temp_directory, "exif_diff.json")
        log.debug(f"writing temporary exif diff json to {exif_diff_path}...")
        with open(exif_diff_path, "w") as f:
            json.dump(exif_diff, f)
        if use_sidecar:
            # The "source_file" (now destination file) may not yet exist
            # so we need to write each file individually.
            for source_file in [diff["SourceFile"] for diff in exif_diff]:
                write_exif(source_file, exif_diff_path)
        else:
            write_exif(root_path, exif_diff_path)


def main():
    parser = argparse.ArgumentParser(
        prog="geotag",
        description="Add GPS metadata to your photos/videos using your Google location history data",
    )
    parser.add_argument(
        "location_history",
        help="path to your google location history json dump",
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
    parser.add_argument(
        "--use-sidecar",
        help="include XMP sidecar files when reading metadata, "
        "write GPS metadata to XMP sidecar instead of writing to the image file",
        action="store_true",
    )
    args = parser.parse_args()

    utc_offset_default = parse_exif_timezone_offset(args.utc_offset_default)
    add_google_location_to_images(
        args.location_history, args.root_path, utc_offset_default, args.use_sidecar
    )
