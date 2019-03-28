import re
import time
import requests

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    collecs = {}
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
        collecs[url] = {
            "image": url,
            "type": "nasa",
            "url": pic_page,
            "copyright": _("NASA Astronomy Picture Of The Day")
        }
    return collecs


def preferences():
    return {
        "name": _("NASA Astronomy Picture Of The Day"),
        "options": {
            "count": {
                "widget": "number",
                "default": 10,
                "label": _("Number of item to retrieve")
            }
        }
    }
