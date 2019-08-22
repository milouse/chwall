import requests
from lxml import html


def fetch_pictures(config):
    pictures = {}
    width = config.get("powder", {}).get("width", 1920)
    if width not in [320, 640, 970, 1920]:
        width = 1920
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
        pictures[url] = {
            "image": url,
            "type": "Powder",
            "url": "https://www.powder.com" + link.attrib["href"],
            "author": link.attrib["title"]
        }
    return pictures


def preferences():
    return {
        "name": "Powder",
        "options": {
            "width": {
                "type": "int",
                "widget": "select",
                "values": [320, 640, 970, 1920],
                "default": 1920
            }
        }
    }
