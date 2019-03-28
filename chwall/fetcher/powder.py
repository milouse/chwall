import requests
from lxml import html

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


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
            "copyright": (_("{title} by {author} (on {source})")
                          .format(title="Picture", source="Powder",
                                  author=link.attrib["title"]))
        }
    return collecs


def preferences():
    return {
        "name": "Powder",
        "options": {
            "width": {
                "type": "int",
                "widget": "select",
                "values": [320, 640, 970, 1920],
                "default": 1920,
                "label": _("Wallpaper width")
            }
        }
    }
