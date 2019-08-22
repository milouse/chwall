import requests
from datetime import date


def fetch_pictures(config):
    pictures = {}
    width = 1600
    if "natgeo" in config and "width" in config["natgeo"] and \
       config["natgeo"]["width"] in [240, 320, 500, 640, 800,
                                     1024, 1600, 2048]:
        width = config["natgeo"]["width"]
    url = "https://www.nationalgeographic.com/photography/photo-of-the-day/" \
          "_jcr_content/.gallery.{}-{}.json"
    t = date.today()
    data = requests.get(url.format(t.year, t.strftime("%m"))).json()
    for p in data["items"]:
        if p["url"] == "https://yourshot.nationalgeographic.com":
            px = p["sizes"]["%d" % width]
            pictures[px] = {
                "image": px,
                "description": p["altText"],
                "author": p["credit"],
                "url": p["full-path-url"],
                "type": "National Geographic"
            }
        else:
            px = p["url"]
            pictures[px] = {
                "image": px,
                "copyright": "{}. {}".format(p["altText"], p["credit"]),
                "url": p["pageUrl"],
                "type": "National Geographic"
            }
    return pictures


def preferences():
    return {
        "name": "National Geographic",
        "options": {
            "width": {
                "type": "int",
                "widget": "select",
                "values": [240, 320, 500, 640, 800, 1024, 1600, 2048],
                "default": 1600
            }
        }
    }
