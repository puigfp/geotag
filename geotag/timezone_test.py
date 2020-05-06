from datetime import datetime, timezone

import pytest
import pytz
from timezonefinder import TimezoneFinder

from .timezone import gps_coords_to_utc_offset


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
    # 2:01AM Paris time doesn't exist
    with pytest.raises(pytz.exceptions.NonExistentTimeError):
        assert gps_coords_to_utc_offset(datetime(2020, 3, 29, 2, 1), lat, lng) == 120

    # ---
    # edge case 2: on 2019.10.27 at 3AM, clocks were turned backward to 2AM
    # ---
    # at 1:59AM Paris time: UTC offset is 2 hours
    assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 1, 59), lat, lng) == 120
    # at 3AM Paris time: UTC offset is 1 hour
    assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 3), lat, lng) == 60
    # 2:01AM Paris time is ambiguous
    with pytest.raises(pytz.exceptions.AmbiguousTimeError):
        assert gps_coords_to_utc_offset(datetime(2019, 10, 27, 2, 1), lat, lng) == 120
