import sys
import requests


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
    collecs = {}
    final_uri = "{}?{}".format(url, "&".join(params))
    data = requests.get(final_uri).json()
    for p in data:
        px = p["urls"]["custom"]
        if p["description"] is None:
            label = "Picture"
        else:
            label = p["description"]
        label = "{} by {} (on Unsplash)".format(label, p["user"]["name"])
        if "location" in p and p["location"]["title"] is not None:
            label = "{}, taken in {}".format(label, p["location"]["title"])
        collecs[px] = {
            "image": px,
            "copyright": label,
            "url": p["links"]["html"],
            "type": "unsplash"
        }
    return collecs
