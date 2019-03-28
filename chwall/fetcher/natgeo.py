import requests
from datetime import date

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    collecs = {}
    width = 1600
    if "natgeo" in config and "width" in config["natgeo"] and \
       config["natgeo"]["width"] in [240, 320, 500, 640, 800,
                                     1024, 1600, 2048]:
        width = config["natgeo"]["width"]
    url = "https://www.nationalgeographic.com/photography/photo-of-the-day/" \
          "_jcr_content/.gallery.{}-{}.json"
    t = date.today()
    data = requests.get(url.format(t.year, t.strftime("%m"))).json()
    for p in data["items"]:
        if p["url"] == "https://yourshot.nationalgeographic.com":
            px = p["sizes"]["%d" % width]
            purl = p["full-path-url"]
            pcredit = (_("{title} by {author} (on {source})")
                       .format(title=p["altText"], author=p["credit"],
                               source="National Geographic"))
        else:
            px = p["url"]
            purl = p["pageUrl"]
            pcredit = ("{}. {} (on National Geographic)"
                       .format(p["altText"], p["credit"]))
        collecs[px] = {
            "image": px,
            "copyright": pcredit,
            "url": purl,
            "type": "natgeo"
        }
    return collecs


def preferences():
    return {
        "name": "National Geographic",
        "options": {
            "width": {
                "type": "int",
                "widget": "select",
                "values": [240, 320, 500, 640, 800, 1024, 1600, 2048],
                "default": 1600,
                "label": _("Wallpaper width")
            }
        }
    }
