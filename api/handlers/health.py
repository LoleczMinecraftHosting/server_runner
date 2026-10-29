from api.api_core import APIHandler
from api.utils import APIReturn


@APIHandler.get("/health", autoauth=False)
def health(headers, query):
    return APIReturn({"status": "ok"})
