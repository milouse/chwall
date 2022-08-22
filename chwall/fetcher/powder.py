import requests
from lxml import html


def fetch_pictures(config):
    pictures = {}
    width = config.get("powder", {}).get("width", 1920)
    if width not in [320, 640, 970, 1920]:
        width = 1920
    content = ""
    # TODO: support https://www.powder.com/photos/
    for page in range(1, 6):
        content += requests.get(
            f"https://www.powder.com/wp-json/ami/v1/lazy-load?paged={page}"
            "&count=20&term_query={%22name%22:%22category%22,%22value%22:"
            "%22Photo%20of%20the%20Day%22}&sort={%22date%22:%22desc%22}"
        ).text
    data = html.fromstring(content)
    for picture in data.cssselect("div.article img.article__figure-image"):
        pics = picture.attrib["srcset"]
        if pics is None or pics == "":
            continue
        url = ""
        for s in pics.split(","):
            us = s.strip().split(" ")
            if us[1] == "{}w".format(width):
                url = us[0]
                break
        if url == "":
            continue
        link = picture.getparent().getparent()
        author = link.getparent().getparent().cssselect("h2.article__title")
        pictures[url] = {
            "image": url,
            "type": "Powder",
            "url": link.attrib["href"],
            "author": author[0].text.strip()
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
