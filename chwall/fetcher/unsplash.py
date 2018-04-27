#!/usr/bin/env python3

import re
import requests
from xml.etree import ElementTree
from urllib.parse import urlsplit


def fetch_pictures(config):
    collecs = {}
    width = 1600
    if "unsplash" in config and "width" in config["unsplash"]:
        width = config["unsplash"]["width"]

    data = ElementTree.fromstring(
        requests.get("https://unsplash.com/rss").text)
    for item in data[0].findall("item"):
        tp = {
            "type": "unsplash",
            "local": False
        }
        data = item.find("description").text
        m = re.search("^\\s+<img src=\"(.+)\" title=\"By .+\">$",
                      data, re.MULTILINE)
        if m is None:
            continue
        u = urlsplit(re.sub("&amp;", "&", m[1]))
        url = "{}://{}{}?w={}&fit=max".format(
            u.scheme, u.netloc, u.path, str(width))
        tp["image"] = url
        m = re.search("^\\s+<a href=\"(.+)\">Download</a> / "
                      "By <a href=\"(.+)\">(.+)</a>$",
                      data, re.MULTILINE)
        if m is None:
            continue
        tp["copyright"] = "Picture by {}".format(m[3])
        tp["url"] = m[1]
        collecs[tp["image"]] = tp
    return collecs
