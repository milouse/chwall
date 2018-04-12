#!/usr/bin/env python3

import re
import requests
from urllib.parse import urlsplit


def fetch_pictures(config):
    collecs = {}
    data = requests.get("https://unsplash.com/rss").text.split("\n")
    tp = None
    width = 1600
    if "unsplash" in config and "width" in config["unsplash"]:
        width = config["unsplash"]["width"]

    for line in data:
        m1 = re.search("^\s+<img src=\"(.+)\" title=\"By .+\">$",
                       line, re.MULTILINE)
        if m1 is not None:
            u = urlsplit(re.sub("&amp;", "&", m1[1]))
            url = "{}://{}{}?w={}&fit=max".format(
                u.scheme, u.netloc, u.path, str(width))
            tp = {
                "image": url,
                "type": "unsplash",
                "local": False
            }
            continue
        m2 = re.search("^\s+<a href=\"(.+)\">Download</a> / "
                       "By <a href=\"(.+)\">(.+)</a>$",
                       line, re.MULTILINE)
        if m2 is not None:
            tp["copyright"] = "Picture by {}".format(m2[3])
            tp["url"] = m2[1]
            collecs[tp["image"]] = tp
    return collecs
