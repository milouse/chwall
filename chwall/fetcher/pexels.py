import requests

from chwall.utils import get_logger

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext

logger = get_logger(__name__)


def fetch_pictures(config):
    px_conf = config.get("pexels", {})
    client_id = px_conf.get("access_key")
    if client_id is None:
        logger.error(
            _("An `access_key' param is required to fetch pictures "
              "from Pexels.")
        )
        return {}
    width = px_conf.get("width", 1600)
    params = {"per_page": px_conf.get("count", 10)}
    if "query" in px_conf:
        params["query"] = px_conf["query"]
        url = "https://api.pexels.com/v1/search"
    else:
        url = "https://api.pexels.com/v1/curated"
    pictures = {}
    data = requests.get(
        url,
        params=params,
        headers={"Authorization": client_id}
    ).json()
    for p in data["photos"]:
        px = p["src"]["original"] + "?auto=compress&width={}".format(width)
        pictures[px] = {
            "image": px,
            "author": p["photographer"],
            "url": p["url"],
            "type": "Pexels"
        }
    return pictures


def preferences():
    return {
        "name": "Pexels",
        "options": {
            "width": {
                "widget": "number",
                "default": 1600
            },
            "count": {
                "widget": "number",
                "default": 10
            },
            "access_key": {
                "widget": "text",
                "label": _("API access key")
            },
            "query": {
                "widget": "text",
                "label": _("Search query")
            }
        }
    }
