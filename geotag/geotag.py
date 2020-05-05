import argparse
import bisect
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from typing import List

from .gps import Location, discard_bad_gps_points, read_google_location_history
from .log import log


def read_exif(root: str) -> List[dict]:
    log.info("reading exif from photos using exiftool...")
    completed = subprocess.run(
        ["exiftool", "-json", "-r", root], capture_output=True, check=True
    )
    return json.loads(completed.stdout)


def write_exif(root_path: str, exif_diff_path: str):
    log.info("writing exif diff to photos using exiftool...")
    subprocess.run(
        ["exiftool", "-overwrite_original", f"-json={exif_diff_path}", "-r", root_path],
        check=True,
    )


def location_to_exif_diff(location: Location, img_path: str) -> dict:
    location_datetime = datetime.fromtimestamp(location.timestamp, tz=timezone.utc)
    return {
        "SourceFile": img_path,
        "GPSDateTime": location_datetime.strftime("%Y:%m:%d %H:%M:%SZ"),
        "GPSTimeStamp": location_datetime.strftime("%H:%M:%S"),
        "GPSDateStamp": location_datetime.strftime("%Y:%m:%d"),
        "EXIF:GPSLatitudeRef": "N",
        "EXIF:GPSLongitudeRef": "E",
        "EXIF:GPSLatitude": f"{location.latitude} N",
        "EXIF:GPSLongitude": f"{location.longitude} E",
        # XXX: it seems we need to write the GPS metadata in EXIF and XMP to make
        # Lightroom able to read it
        "XMP:GPSLatitude": f"{location.latitude} N",
        "XMP:GPSLongitude": f"{location.longitude} E",
    }


def get_exif_diff(
    list_exif: List[dict], location_history: List[Location], utc_offset: float
) -> List[dict]:
    log.info("computing exif diff")
    location_timestamps = [location.timestamp for location in location_history]
    date_interval = (
        datetime.fromtimestamp(location_timestamps[0], tz=timezone.utc),
        datetime.fromtimestamp(location_timestamps[-1], tz=timezone.utc),
    )

    exif_diff = []
    for img_exif in list_exif:
        img_path = img_exif["SourceFile"]
        if "DateTimeOriginal" not in img_exif:
            log.warning(f'skipping "{img_path}", could not find date/time metadata')
            continue
        if "GPSPosition" in img_exif:
            log.warning(f'skipping "{img_path}", gps info already present')
            continue

        img_date = datetime.strptime(
            img_exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S",
        ).replace(tzinfo=timezone(timedelta(hours=utc_offset)))
        if not date_interval[0] <= img_date < date_interval[1]:
            log.warning(
                f'skipping "{img_path}", {img_date} is out of location history range '
                f"[{date_interval[0]}, {date_interval[1]}]"
            )
            continue

        img_timestamp = img_date.timestamp()
        i = bisect.bisect_left(location_timestamps, img_timestamp)

        closest_location = min(
            [location_history[i], location_history[i + 1]],
            key=lambda location: abs(location.timestamp - img_timestamp),
        )
        delta_timestamp = abs(closest_location.timestamp - img_timestamp)
        if delta_timestamp > 60 * 60:  # 1 hour
            log.warning(
                f'skipping "{img_path}", timestamp ({img_timestamp}) is too far from'
                f"the closest history timestamp (delta={delta_timestamp}s)"
            )
            continue
        exif_diff.append(location_to_exif_diff(closest_location, img_path))

    return exif_diff


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
