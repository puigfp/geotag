import bisect
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytz
from timezonefinder import TimezoneFinder

from .location_history import Location
from .log import log

tf = TimezoneFinder(in_memory=True)


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


def gps_coords_to_utc_offset(dt: datetime, lat: float, lng: float) -> int:
    """
    Returns the UTC offset (as a signed number of minutes) of a given location at a
    given datetime.
    Note: if the datetime has no timezone information, this function considers the
    timezone to be the timezone associated with the provided GPS coordinates (please
    see the test for more details).
    """
    # tz_str: timezone string (eg, "Europe/Paris")
    tz_str = tf.timezone_at(lat=lat, lng=lng)
    assert tz_str is not None

    # tz: pytz tzinfo object
    tz = pytz.timezone(tz_str)

    # convert dt to naive datetime if necesary
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz).replace(tzinfo=None)

    # because of daylight savings, the UTC offset depends on the date
    offset = tz.utcoffset(dt)
    return int(offset.total_seconds()) // 60


# regex for parsing the EXIF time offset format ("±HH:MM")
REGEX_TIMEZONE_OFFSET = re.compile(
    r"(?P<sign>\+|-)?(?P<hours>\d{2}):(?P<minutes>\d{2})"
)


def parse_exif_timezone_offset(s: str) -> int:
    """
    Parses an EXIF time offset ("±HH:MM") and returns a signed number of minutes.
    """
    match = REGEX_TIMEZONE_OFFSET.fullmatch(s)
    if match is None:
        raise Exception(f'"{s}" isn\'t a valid EXIF time offset string ("±HH:MM")')
    groups = match.groupdict()

    sign = +1 if groups["sign"] in ("+", None) else -1
    hours = int(groups["hours"])
    minutes = int(groups["minutes"])
    return sign * (60 * hours + minutes)


def format_exif_timezone_offset(offset: int) -> str:
    """
    Serializes a number of minutes to a EXIF time offset ("±HH:MM") string.
    """
    sign = 1 if offset >= 0 else -1
    if sign == -1:
        offset = -offset
    sign_str = "+" if sign == 1 else "-"
    hours_str = str(offset // 60).zfill(2)
    minutes_str = str(offset % 60).zfill(2)
    return f"{sign_str}{hours_str}:{minutes_str}"


def get_file_exif_diff(
    img_exif: dict, img_date: datetime, location: Location,
) -> Optional[dict]:
    diff = {"SourceFile": img_exif["SourceFile"]}

    # update date/time/utc offset
    try:
        utc_offset_target = gps_coords_to_utc_offset(
            img_date, lat=location.latitude, lng=location.longitude
        )
        diff = {
            **diff,
            "DateTimeOriginal": img_date.astimezone(
                tz=timezone(timedelta(minutes=utc_offset_target))
            ).strftime("%Y:%m:%d %H:%M:%S"),
            "OffsetTimeOriginal": format_exif_timezone_offset(utc_offset_target),
        }
        print(diff, utc_offset_target)
    except pytz.exceptions.AmbiguousTimeError as e:
        log.error(
            f'skipping "{img_path}" date/time/utc offset update, '
            f"encountered an ambiguous time error: {e}"
        )

    # update location
    location_datetime = datetime.fromtimestamp(location.timestamp, tz=timezone.utc)
    diff = {
        **diff,
        "GPSDateTime": location_datetime.strftime("%Y:%m:%d %H:%M:%SZ"),
        "GPSTimeStamp": location_datetime.strftime("%H:%M:%S"),
        "GPSDateStamp": location_datetime.strftime("%Y:%m:%d"),
        # XXX: it seems we need to write the GPS metadata in EXIF and XMP to make
        # Lightroom able to read it
        "EXIF:GPSLatitude": location.latitude,
        "EXIF:GPSLongitude": location.longitude,
        "XMP:GPSLatitude": location.latitude,
        "XMP:GPSLongitude": location.longitude,
    }

    return diff


def get_exif_diff(
    list_exif: List[dict], location_history: List[Location], utc_offset_default: int
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

        # infer image original date UTC offset
        utc_offset_str = img_exif.get("OffsetTimeOriginal")
        utc_offset = (
            parse_exif_timezone_offset(utc_offset_str)
            if utc_offset_str is not None
            else utc_offset_default
        )

        # parse image original date
        img_date = datetime.strptime(
            img_exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S",
        ).replace(tzinfo=timezone(timedelta(minutes=utc_offset)))

        # find closest location
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
            return None

        # append diff
        img_exif_diff = get_file_exif_diff(img_exif, img_date, closest_location)
        if img_exif_diff is not None:
            exif_diff.append(img_exif_diff)

    return exif_diff
