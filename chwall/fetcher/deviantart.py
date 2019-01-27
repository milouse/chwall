#!/usr/bin/env python3

import os
import re
import requests
from xml.etree import ElementTree


def fetch_pictures(config):
    collecs = {}
    url = "https://backend.deviantart.com/rss.xml?type=deviation&q={}"
    if "deviantart" not in config or len(config["deviantart"]) == 0:
        return {}
    for q in config["deviantart"]:
        data = ElementTree.fromstring(requests.get(url.format(q)).text)
        for item in data[0].findall("item"):
            title = item.find("title").text
            author = item.find(
                        "{http://search.yahoo.com/mrss/}credit").text
            pic_page = item.find("link").text
            try:
                da_target = os.path.basename(
                    item.find(
                        "{http://search.yahoo.com/mrss/}content")
                    .attrib["url"])
            except AttributeError:
                continue
            dadl = "https://www.deviantart.com/download"
            scrap = requests.get(pic_page)
            pic_url = None
            m = re.search(
                "^\\s+href=\"({dadl}/[0-9]+/{target}\\?token=[^\"]+)\"$"
                .format(dadl=dadl, target=da_target),
                scrap.text, re.MULTILINE)
            if m:
                # directly fetch linked picture
                r = requests.get(re.sub("&amp;", "&", m[1]),
                                 cookies=scrap.cookies)
                pic_url = r.url
                # prefer download url over preview picture
            else:
                m = re.search(
                    "data-super-full-img=\"([^\"]+{target})\""
                    .format(target=da_target), scrap.text)
                if m:
                    pic_url = m[1]
            if pic_url is None:
                continue
            collecs[pic_url] = {
                "image": pic_url,
                "type": "deviantart",
                "url": pic_page,
                "copyright": "{} by {}".format(title, author)
            }
    return collecs
