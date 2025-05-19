import logging
import os

from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from logiclayer import LogicLayer
from logiclayer_complexity import EconomicComplexityModule
from tesseract_olap import OlapServer
from tesseract_olap.logiclayer import TesseractModule

from datausa.auth import StaticAuthProvider
from datausa.calculations import CalculationsModule

logger = logging.getLogger(__name__)

# PARAMETERS ===================================================================

# These parameters are required and will prevent execution if not set
olap_backend = os.environ["TESSERACT_BACKEND"]
olap_schema = os.environ["TESSERACT_SCHEMA"]

# These parameters are optional
olap_cache = os.environ.get("TESSERACT_CACHE", "")
debug_token = os.environ.get("TESSERACT_DEBUG_TOKEN")
app_debug = os.environ.get("TESSERACT_DEBUG")

app_debug = bool(app_debug)

# ASGI app =====================================================================
olap = OlapServer(backend=olap_backend, schema=olap_schema, cache=olap_cache)
auth = StaticAuthProvider(debug_token) if debug_token else None

layer = LogicLayer(debug=app_debug)

mod_tsrc = TesseractModule(olap, auth=auth, debug=app_debug)
layer.add_module("/tesseract", mod_tsrc)

mod_cmplx = EconomicComplexityModule(olap, auth=auth, debug=app_debug)
layer.add_module("/complexity", mod_cmplx)

mod_calcs = CalculationsModule(olap, auth=auth, debug=app_debug)
layer.add_module("/calcs", mod_calcs)

layer.add_static("/ui", "./etc/static/", html=True)


@layer.route("/", response_class=RedirectResponse, status_code=302)
def route_index() -> str:
    """Define a redirection of the domain root to the Tesseract UI static page."""
    return "/ui/"


@layer.route("/robots.txt", include_in_schema=False)
def route_robots() -> Response:
    """Define the robots.txt directive for the subdomain."""
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


logger.info("App is ready to accept connections")
