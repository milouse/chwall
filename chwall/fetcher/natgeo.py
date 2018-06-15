#!/usr/bin/env python3

import requests
from datetime import date


def fetch_pictures(config):
    collecs = {}
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
        url = p["url"] + p["sizes"]["%d" % width]
        collecs[url] = {
            "image": url,
            "copyright": "{} by {}".format(p["altText"], p["credit"]),
            "url": p["full-path-url"],
            "type": "natgeo",
            "local": False
        }
    return collecs
