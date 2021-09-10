from __future__ import annotations  # see https://stackoverflow.com/a/33533514

import json
import math
from dataclasses import dataclass
from typing import List

from .log import log


@dataclass
class Location:
    timestamp: int
    latitude: float
    longitude: float

    @staticmethod
    def from_google_json(d: dict) -> Location:
        return Location(
            timestamp=int(d["timestampMs"]) // 1000,
            latitude=int(d["latitudeE7"]) / 10 ** 7,
            longitude=int(d["longitudeE7"]) / 10 ** 7,
        )


def dist_gps(lat1: float, long1: float, lat2: float, long2: float) -> float:
    # compute distance between 2 GPS points using the haversine formula
    # reference: https://www.movable-type.co.uk/scripts/latlong.html
    lat1, long1, lat2, long2 = (math.radians(e) for e in (lat1, long1, lat2, long2))
    a = (
        math.sin((lat1 - lat2) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((long1 - long2) / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371e3 * c


def speed_gps(loc1: Location, loc2: Location) -> float:
    # compute the average speed between 2 locations (result in meters per second)
    if loc1.timestamp == loc2.timestamp:
        return 0.0
    d = dist_gps(loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude)
    t = abs(loc1.timestamp - loc2.timestamp)
    return d / t  # m/s


def discard_bad_gps_points(location_history: List[Location]) -> List[Location]:
    log.info("discarding bad points from location history...")
    location_history_clean = []
    for i in range(len(location_history)):
        if 0 < i < len(location_history) - 1:
            # XXX:
            # It turns out the Google Location history isn't perfect, and we can expect
            # to find some bad GPS points. In my data, I found multiple examples of
            # lonely outliers: location n is ok, location n+1 is be very very far from
            # location n, and location n+2 is close to location n. In such cases, a
            # simple fix can be to remove location n+1 from the history.
            speed_keep = 3.6 * speed_gps(
                location_history_clean[-1], location_history[i]
            )

            if speed_keep < 90.0:
                speed_discard = 3.6 * speed_gps(
                    location_history_clean[-1], location_history[i + 1]
                )
            else:
                speed_discard = min(
                    3.6 * speed_gps(location_history_clean[-1], location_history[j])
                    for j in range(i + 1, min(i + 1 + 5, len(location_history)))
                )
            if speed_keep > 30.0 and speed_keep > 3 * speed_discard:
                continue

        location_history_clean.append(location_history[i])

    n_discarded = len(location_history) - len(location_history_clean)
    if n_discarded > 0:
        log.warning(
            f"discarded {n_discarded}/{len(location_history)} "
            f"({100 * n_discarded/len(location_history):.2f}%) GPS points"
        )

    return location_history_clean


def read_google_location_history(path: str) -> List[Location]:
    log.info("reading/parsing location history json...")
    with open(path, "r") as f:
        location_history_json = json.load(f)

    log.info("processing location history json...")
    location_history = [
        Location.from_google_json(d) for d in location_history_json["locations"]
    ]
    location_history.sort(key=lambda location: location.timestamp)

    return location_history
