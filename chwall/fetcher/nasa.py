#!/usr/bin/env python3

import re
import time
import requests


def fetch_pictures(config):
    collecs = {}
    curday = time.time()
    for i in range(10):
        pic_page = "https://apod.nasa.gov/apod/ap{}.html".format(
            time.strftime("%y%m%d", time.localtime(curday)))
        # Go to yesterday
        curday = curday - 86400
        data = requests.get(pic_page)
        for line in data.text.split("\n"):
            m = re.search("^<a href=\"(image/[0-9]{4}/.+)\">$",
                          line, re.MULTILINE)
            if m is None:
                continue
            url = "https://apod.nasa.gov/apod/{}".format(m[1])
            collecs[url] = {
                "image": url,
                "type": "nasa",
                "local": False,
                "url": pic_page,
                "copyright": "NASA Astronomy Picture of the Day"
            }
            break
    return collecs
