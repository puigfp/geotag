from datetime import datetime, timedelta, timezone

import pytest
import pytz
from timezonefinder import TimezoneFinder

from .exif import (
    format_exif_timezone_offset,
    gps_coords_to_utc_offset,
    parse_exif_timezone_offset,
)


@pytest.mark.parametrize(
    "s,expected", [("12:31", 751), ("+02:31", 151), ("-12:02", -722),],
)
def test_parse_exif_timezone_offset_ok(s: str, expected: int):
    assert parse_exif_timezone_offset(s) == expected


@pytest.mark.parametrize(
    "s", ["2:31", "*02:31", "+02:321"],
)
def test_parse_exif_timezone_offset_fail(s: str):
    # invalid offset strings should trigger an exception
    with pytest.raises(Exception):
        parse_exif_timezone_offset(s)


@pytest.mark.parametrize(
    "offset,expected", [(151, "+02:31"), (-722, "-12:02"),],
)
def test_format_exif_timezone_offset(offset, expected):
    assert format_exif_timezone_offset(offset) == expected
    # x -> parse(format(x)) should be the identity function
    assert parse_exif_timezone_offset(format_exif_timezone_offset(offset)) == offset


def test_gps_coords_to_utc_offset():
    lat, lng = 48.8566, 2.3522  # Paris 🇫🇷

    tf = TimezoneFinder(in_memory=True)
    assert tf.timezone_at(lat=lat, lng=lng) == "Europe/Paris"

    utc = timezone.utc

    # ---
    # easy scenarios
    # ---
    # Paris Summer time
    assert gps_coords_to_utc_offset(datetime(2020, 5, 5), lat, lng) == 120
    # Paris Winter time
    assert gps_coords_to_utc_offset(datetime(2020, 1, 5), lat, lng) == 60

    # ---
    # edge case 1: on 2020.02.29 at 2AM, clocks were forwarded to 3AM
    # ---
    # at 1:59AM Paris time: UTC offset is 1 hour
    assert gps_coords_to_utc_offset(datetime(2020, 3, 29, 1, 59), lat, lng) == 60
    assert (
        gps_coords_to_utc_offset(datetime(2020, 3, 29, 0, 59, tzinfo=utc), lat, lng)
        == 60
    )
    # at 3AM Paris time: UTC offset is 2 hours
    assert gps_coords_to_utc_offset(datetime(2020, 3, 29, 3), lat, lng) == 120
    assert (
        gps_coords_to_utc_offset(datetime(2020, 3, 29, 1, tzinfo=utc), lat, lng) == 120
    )
    # 2:01AM doesn't exist
    with pytest.raises(pytz.exceptions.NonExistentTimeError):
        assert gps_coords_to_utc_offset(datetime(2020, 3, 29, 2, 1), lat, lng) == 120

    # ---
    # edge case 2: on 2019.10.27 at 3AM, clocks were turned backward to 2AM
    # ---
    # at 1:59AM Paris time: UTC offset is 2 hours
    assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 1, 59), lat, lng) == 120
    # at 3AM Paris time: UTC offset is 1 hour
    assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 3), lat, lng) == 60
    # 2:01AM is ambiguous
    # XXX: right now, photos taken at an ambiguous time will make the script crash
    with pytest.raises(pytz.exceptions.AmbiguousTimeError):
        assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 2, 1), lat, lng) == 120
