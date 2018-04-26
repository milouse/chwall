#!/usr/bin/env python3

import os
import re
import requests
from xml.etree import ElementTree


def fetch_pictures(config):
    collecs = {}
    already_done = []
    url = "https://backend.deviantart.com/rss.xml?type=deviation&q={}"
    if "deviantart" not in config or len(config["deviantart"]) == 0:
        return {}
    for q in config["deviantart"]:
        data = ElementTree.fromstring(requests.get(url.format(q)).text)
        for child in data[0].findall("item"):
            title = child.find("title").text
            author = child.find(
                        "{http://search.yahoo.com/mrss/}credit").text
            pic_page = child.find("link").text
            try:
                da_target = os.path.basename(
                    child.find(
                        "{http://search.yahoo.com/mrss/}content")
                    .attrib["url"])
            except AttributeError:
                continue
            scrap = requests.get(pic_page).text
            for line in scrap.split("\n"):
                m = re.search(
                    "data-super-full-img=\"([^\"]+{target})\""
                    .format(target=da_target),
                    line)
                if m is None:
                    continue
                collecs[m[1]] = {
                    "image": m[1],
                    "type": "deviantart",
                    "local": False,
                    "url": pic_page,
                    "copyright": "{} by {}".format(title, author)
                }
    return collecs
