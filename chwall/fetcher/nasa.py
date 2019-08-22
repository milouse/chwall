import re
import time
import requests


def fetch_pictures(config):
    pictures = {}
    nb_pic = 10
    if "nasa" in config and "count" in config["nasa"]:
        nb_pic = config["nasa"]["count"]
    curday = time.time()
    for i in range(nb_pic):
        pic_page = "https://apod.nasa.gov/apod/ap{}.html".format(
            time.strftime("%y%m%d", time.localtime(curday)))
        # Go to yesterday
        curday = curday - 86400
        data = requests.get(pic_page).text
        m = re.search("^<a href=\"(image/[0-9]{4}/.+)\">$",
                      data, re.MULTILINE)
        if m is None:
            continue
        url = "https://apod.nasa.gov/apod/{}".format(m[1])
        pictures[url] = {
            "image": url,
            "type": "NASA",
            "url": pic_page,
            "copyright": "Astronomy Picture Of The Day"
        }
    return pictures


def preferences():
    return {
        "name": "NASA Astronomy Picture Of The Day",
        "options": {
            "count": {
                "widget": "number",
                "default": 10
            }
        }
    }
