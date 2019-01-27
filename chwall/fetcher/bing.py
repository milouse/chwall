#!/usr/bin/env python3

import re
import requests


def fetch_pictures(config):
    collecs = {}
    already_done = []
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0" \
          "&n=10&mkt={}"
    if "bing" in config:
        i18n_src = config["bing"]
    else:
        i18n_src = ['en-US', 'fr-FR']
    for l in i18n_src:
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
                "type": "bing"
            }
    return collecs
