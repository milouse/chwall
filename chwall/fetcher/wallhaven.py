from chwall.fetcher import requests_get

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    wh_conf = config.get("wallhaven", {})
    search_url = "https://wallhaven.cc/api/v1/search"
    params = {
        "sorting": wh_conf.get("sorting", "random"),
        "purity": wh_conf.get("purity", "100"),
        "categories": wh_conf.get("categories", "100")
    }
    width = wh_conf.get("width", 0)
    height = wh_conf.get("height", 0)
    atleast = f"{width}x{height}"
    if atleast != "0x0":
        params["atleast"] = atleast
    color = wh_conf.get("color")
    if color:
        params["colors"] = color
    ratio = wh_conf.get("ratio")
    if ratio:
        params["ratios"] = ratio
    query = wh_conf.get("query")
    if query:
        params["q"] = query
    data = requests_get(search_url, params=params).json()
    pictures = {}
    for pix in data.get("data", []):
        pix_uri = pix["path"]
        pictures[pix_uri] = {
            "image": pix_uri,
            "url": pix["url"],
            "copyright": pix["source"],
            "type": "Wallhaven"
        }
    return pictures


def preferences():
    return {
        "name": "Wallhaven",
        "options": {
            "width": {"widget": "number"},
            "height": {
                "widget": "number",
                "label": _("Wallpaper height")
            },
            "ratio": {
                "widget": "select",
                "values": [
                    ("landscape", _("Landscape")),
                    ("portrait", _("Portrait")),
                    "16x9", "16x10",            # wide
                    "21x9", "32x9", "48x9",     # ultrawide
                    "9x16", "10x16", "9x18",    # portrait
                    "1x1", "3x2", "4x3", "5x4"  # square
                ],
                "label": _("Ratio")
            },
            "color": {
                "widget": "color",
                "label": _("Main color")
            },
            "sorting": {
                "widget": "select",
                "values": [
                    ("relevance", _("Relevance")),
                    ("random", _("Random")),
                    ("date_added", _("Date Added")),
                    ("views", _("Views")),
                    ("favorites", _("Favorites")),
                    ("toplist", _("Toplist")),
                    ("hot", _("Hot"))
                ],
                "default": "random",
                "label": _("Sorting order")
            },
            "purity": {
                "widget": "select",
                "values": [
                    ("100", _("SFW")),
                    ("010", _("Sketchy")),
                    ("001", _("NSFW")),
                    ("011", _("Sketchy + NSFW")),
                    ("111", _("All"))
                ],
                "default": "100",
                "label": _("Content filtering")
            },
            "categories": {
                "widget": "select",
                "values": [
                    ("100", _("General")),
                    ("010", _("Anime")),
                    ("001", _("People")),
                    ("110", _("General + Anime")),
                    ("011", _("Anime + People")),
                    ("101", _("General + People")),
                    ("111", _("All"))
                ],
                "default": "100",
                "label": _("Categories")
            },
            "query": {"widget": "text"}
        }
    }
