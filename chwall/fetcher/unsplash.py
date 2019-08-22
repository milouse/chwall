import sys
import requests

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    width = 1600
    nb_pic = 10
    params = ["w=1600"]
    client_id = None
    if "unsplash" in config:
        if "width" in config["unsplash"]:
            width = config["unsplash"]["width"]
            params[0] = "w=%d" % width
        if "access_key" in config["unsplash"]:
            client_id = config["unsplash"]["access_key"]
        if "count" in config["unsplash"]:
            nb_pic = config["unsplash"]["count"]
        if "query" in config["unsplash"]:
            params.append("query=" + config["unsplash"]["query"])
        if "collections" in config["unsplash"]:
            params.append(
                "collections=" + ",".join(config["unsplash"]["collections"]))
    if client_id is None:
        print("WARNING: Unsplash has discontinued their RSS feed. Thus "
              "an `access_key' param is now required.", file=sys.stderr)
        return {}
    params.append("count=%d" % nb_pic)
    url = "https://api.unsplash.com/photos/random"
    params.append("client_id=" + client_id)
    pictures = {}
    final_uri = "{}?{}".format(url, "&".join(params))
    data = requests.get(final_uri).json()
    for p in data:
        px = p["urls"]["custom"]
        if p["description"] is None:
            label = _("Picture")
        else:
            # Avoid descriptions to be on several lines
            label = p["description"]
            # Avoid long descriptions
            if len(label) > 200:
                label = label[0:200] + "…"
        if "location" in p and p["location"]["title"] is not None:
            label = (_("{desc}, taken in {location}")
                     .format(desc=label, location=p["location"]["title"]))
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
            "access_key": {
                "widget": "text",
                "label": _("API access_key")
            },
            "query": {
                "widget": "text",
                "label": _("Complementary query")
            },
            "collections": {
                "widget": "list"
            }
        }
    }
