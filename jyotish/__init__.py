import logging

# Core modules with no heavyweight dependencies
from . import panchang, dasha
from . import flags, aspects, chart, ai_prompt, pdf_export

# utils requires streamlit + geopy + timezonefinder — guard for test environments
try:
    from . import utils
except ImportError:
    utils = None  # type: ignore[assignment]

# astro requires pyswisseph — guard for test environments
try:
    from . import astro
except ImportError:
    astro = None  # type: ignore[assignment]

# Root logger — handlers are added by the host app (Streamlit).
logging.getLogger("jyotish").addHandler(logging.NullHandler())
