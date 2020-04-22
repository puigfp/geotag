import argparse
import bisect
import json
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import List

log = logging.getLogger("geotag")
log_sh = logging.StreamHandler(sys.stderr)
log_sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
log.addHandler(log_sh)
log.setLevel(logging.DEBUG)


@dataclass
class Location:
    timestamp: int
    latitude: float
    longitude: float
    accuracy: int


def read_google_location_history(path: str) -> List[Location]:
    log.info("reading/parsing location history json...")
    with open(path, "r") as f:
        location_history_json = json.load(f)

    log.info("processing location history json...")
    location_history = [
        Location(
            timestamp=int(elem["timestampMs"]) // 1000,
            latitude=float(elem["latitudeE7"]) / 10 ** 7,
            longitude=float(elem["longitudeE7"]) / 10 ** 7,
            accuracy=int(elem["accuracy"]),
        )
        for elem in location_history_json["locations"]
    ]
    location_history.sort(key=lambda location: location.timestamp)

    return location_history


def read_exif(root: str) -> List[dict]:
    log.info("reading exif from photos using exiftool...")
    completed = subprocess.run(
        ["exiftool", "-json", root], capture_output=True, check=True
    )
    return json.loads(completed.stdout)


def write_exif(root_path: str, exif_diff_path: str):
    log.info("writing exif diff to photos using exiftool...")
    subprocess.run(
        ["exiftool", f"-json={exif_diff_path}", root_path], check=True,
    )


def location_to_exif_diff(location: Location, img_path: str) -> dict:
    return {
        "SourceFile": img_path,
        "GPSDateTime": (
            datetime.fromtimestamp(location.timestamp).strftime("%Y:%m:%d %H:%M:%SZ")
        ),
        "GPSTimeStamp": datetime.fromtimestamp(location.timestamp).strftime("%H:%M:%S"),
        "GPSDateStamp": datetime.fromtimestamp(location.timestamp).strftime("%Y:%m:%d"),
        "GPSLatitudeRef": "N",
        "GPSLongitudeRef": "E",
        "GPSLatitude": location.latitude,
        "GPSLongitude": location.longitude,
    }


def get_exif_diff(
    list_exif: List[dict], location_history: List[Location]
) -> List[dict]:
    log.info("computing exif diff")
    location_timestamps = [location.timestamp for location in location_history]
    date_interval = (
        datetime.fromtimestamp(location_timestamps[0]),
        datetime.fromtimestamp(location_timestamps[-1]),
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

        img_date = datetime.strptime(img_exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
        if not date_interval[0] <= img_date < date_interval[1]:
            log.warning(
                f'skipping "{img_path}", {img_date} is out of location history range '
                f"[{datetime.fromtimestamp(location_timestamps[0])}, "
                f"{datetime.fromtimestamp(location_timestamps[-1])}]"
            )
            continue

        # Unfortunately, the datetime present in the EXIF is stored in a human readable
        # format that doesn't include timezone information. The following lines assume
        # that the datetime stored inside the image is in the UTC timezone, which may
        # not be the case depending on how your camera's time is was configured.
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


def add_google_location_to_images(location_history_path: str, root_path: str):
    location_history = read_google_location_history(location_history_path)
    timestamps = [loc.timestamp for loc in location_history]
    exif = read_exif(root_path)
    exif_diff = get_exif_diff(exif, location_history)
    with tempfile.TemporaryDirectory() as temp_directory:
        exif_diff_path = os.path.join(temp_directory, "exif_diff.json")
        log.debug(f"writing temporary exif diff json to {exif_diff_path}...")
        with open(exif_diff_path, "w") as f:
            json.dump(exif_diff, f)
        write_exif(root_path, exif_diff_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "location_history", help="path to your google location history json dump",
    )
    parser.add_argument(
        "root_path", help="path to the photos you want to add GPS info to"
    )
    args = parser.parse_args()
    add_gps_exif(args.location_history, args.root_path)


if __name__ == "__main__":
    main()
