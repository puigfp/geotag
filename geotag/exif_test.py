from datetime import datetime, timedelta, timezone

import pytest

from .exif import (
    format_exif_timezone_offset,
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
