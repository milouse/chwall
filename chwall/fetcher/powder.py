#!/usr/bin/env python3

import requests
from lxml import html


def fetch_pictures(config):
    collecs = {}
    width = 1920
    if "powder" in config and "width" in config["powder"] and \
       config["powder"]["width"] in [320, 640, 970, 1920]:
        width = config["powder"]["width"]
    data = html.fromstring(
        requests.get("https://www.powder.com/photo-of-the-day/").text)
    for item in data.cssselect("article.hentry img.entry-image"):
        pics = item.attrib["data-srcset"]
        if pics is None or pics == "":
            continue
        url = ""
        for s in pics.split(","):
            us = s.split(" ")
            if us[1] == "{}w".format(width):
                url = us[0]
                break
        if url == "":
            continue
        link = item.getparent()
        collecs[url] = {
            "image": url,
            "type": "powder",
            "url": "https://www.powder.com" + link.attrib["href"],
            "copyright": "Picture by {}".format(link.attrib["title"])
        }
    return collecs
