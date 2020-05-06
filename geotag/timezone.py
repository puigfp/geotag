from datetime import datetime

import pytz
from timezonefinder import TimezoneFinder

tf = TimezoneFinder(in_memory=True)


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
