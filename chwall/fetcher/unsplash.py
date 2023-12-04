from chwall.fetcher import requests_get
from chwall.utils import get_logger

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext

logger = get_logger(__name__)


def fetch_pictures(config):
    us_conf = config.get("unsplash", {})
    client_id = us_conf.get("access_key")
    if client_id is None:
        logger.error(
            _("Unsplash has discontinued their RSS feed. Thus "
              "an ‘access_key’ param is now required.")
        )
        return {}
    width = us_conf.get("width", 1600)
    nb_pic = us_conf.get("count", 10)
    ct_fltr = us_conf.get("content_filter", "low")
    params = {
        "client_id": client_id,
        "count": nb_pic,
        "content_filter": ct_fltr
    }
    if "query" in us_conf:
        params["query"] = us_conf["query"]
    if "collections" in us_conf:
        params["collections"] = ",".join(us_conf["collections"])
    url = "https://api.unsplash.com/photos/random"
    pictures = {}
    data = requests_get(url, params=params).json()
    for p in data:
        px = "{u}&w={w}".format(u=p["urls"]["raw"], w=width)
        if p["description"] is None:
            label = _("Picture")
        else:
            # Avoid descriptions to be on several lines
            label = p["description"]
            # Avoid long descriptions
            if len(label) > 200:
                label = label[0:200] + "…"
        location = p.get("location", {}).get("title", "")
        if location is not None and location != "":
            label = _(f"{label}, taken in {location}")
        pictures[px] = {
            "image": px,
            "description": label,
            "author": p["user"]["name"],
            "url": p["links"]["html"],
            "type": "Unsplash"
        }
    return pictures


def preferences():
    return {
        "name": "Unsplash",
        "options": {
            "width": {
                "widget": "number",
                "default": 1600
            },
            "count": {
                "widget": "number",
                "default": 10
            },
            "content_filter": {
                "widget": "select",
                "values": [
                    ("low", _("Low")),
                    ("high", _("High"))
                ],
                "default": "low",
                "label": _("Content filtering")
            },
            "access_key": {"widget": "text"},
            "query": {
                "widget": "text",
                "label": _("Complementary query")
            },
            "collections": {"widget": "list"}
        }
    }
