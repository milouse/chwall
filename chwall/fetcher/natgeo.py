import requests
from datetime import date


def fetch_pictures(config):
    pictures = {}
    url = "https://www.nationalgeographic.com/photography/photo-of-the-day/" \
          "_jcr_content/.gallery.{}-{}.json"
    t = date.today()
    data = requests.get(url.format(t.year, t.strftime("%m"))).json()
    for p in data["items"]:
        px = p["image"]["uri"]
        pictures[px] = {
            "image": px,
            "copyright": "{} - {}".format(p["image"]["title"],
                                          p["image"]["credit"]),
            "url": p["pageUrl"],
            "type": "National Geographic"
        }
    return pictures


def preferences():
    return {
        "name": "National Geographic"
    }
