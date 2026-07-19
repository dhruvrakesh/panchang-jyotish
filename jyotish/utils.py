import logging
from typing import Optional, Tuple
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import pytz
import streamlit as st

logger = logging.getLogger("jyotish.utils")


@st.cache_data(ttl=86400, show_spinner=False)
def geocode_place(place: str) -> Optional[Tuple[float, float]]:
    """Geocode a place name to (lat, lon).  Results are cached for 24 h (BUG-06 fix)."""
    try:
        geolocator = Nominatim(user_agent="jyotish-app", timeout=5)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        loc = geocode(place)
        if loc:
            return (loc.latitude, loc.longitude)
        logger.warning("Nominatim returned no result for place=%r", place)
    except Exception:
        logger.exception("Geocoding failed for place=%r", place)
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def tz_from_latlon(lat: float, lon: float) -> Optional[str]:
    """Resolve IANA timezone name from lat/lon.  Results are cached for 24 h."""
    try:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=lat, lng=lon)
        return tz
    except Exception:
        logger.exception("TimezoneFinder failed for lat=%s lon=%s", lat, lon)
        return None


def coerce_tz(tzname: Optional[str]):
    if not tzname:
        return None
    try:
        return pytz.timezone(tzname)
    except Exception:
        logger.warning("Unknown timezone name: %r", tzname)
        return None
