#!/usr/bin/env python3

import re
import requests
from xml.etree import ElementTree
from urllib.parse import urlsplit


def fetch_from_rss(config, width):
    collecs = {}
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
        tp["copyright"] = "Picture by {} (on Unsplash)".format(m[3])
        tp["url"] = m[1]
        collecs[tp["image"]] = tp
    return collecs


def fetch_pictures(config):
    width = 1600
    params = ["w=1600"]
    client_id = None
    if "unsplash" in config:
        if "width" in config["unsplash"]:
            width = config["unsplash"]["width"]
            params[0] = "w=%d" % width
        if "access_key" in config["unsplash"]:
            client_id = config["unsplash"]["access_key"]
        if "count" in config["unsplash"]:
            params.append("count=%d" % config["unsplash"]["count"])
        if "query" in config["unsplash"]:
            params.append("query=" + config["unsplash"]["query"])
        if "collections" in config["unsplash"]:
            params.append(
                "collections=" + ",".join(config["unsplash"]["collections"]))
    if client_id is None:
        return fetch_from_rss(config, width)
    url = "https://api.unsplash.com/photos/random"
    params.append("client_id=" + client_id)
    collecs = {}
    data = requests.get("{}?{}".format(url, "&".join(params))).json()
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
            "type": "unsplash",
            "local": False
        }
    return collecs
