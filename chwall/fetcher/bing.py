#!/usr/bin/env python3

import re
import requests


def fetch_pictures(config):
    if "bing" not in config:
        return {}
    collecs = {}
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0" \
          "&n=10&mkt={}"
    already_done = []
    for l in config["bing"]:
        lu = "{}[0-9]{{10}}".format(l.upper())
        data = requests.get(url.format(l)).json()
        for p in data["images"]:
            ad = re.sub(lu, "", p["url"])
            if ad in already_done:
                continue
            already_done.append(ad)
            px = "https://www.bing.com{}".format(p["url"])
            collecs[px] = {
                "image": px,
                "copyright": p["copyright"],
                "url": p["copyrightlink"],
                "type": "bing",
                "local": False
            }
    return collecs
