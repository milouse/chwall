import requests
from datetime import date


def fetch_pictures(config):
    pictures = {}
    t = date.today()
    year = t.year
    month_label = ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november",
                   "december"]
    month_idx = t.month - 2
    if month_idx == -1:
        month_idx = 11
        year -= 1
    month = month_label[month_idx]
    final_uri = "https://www.nationalgeographic.co.uk/page-data/" \
        f"photo-of-the-day/{year}/{month}/page-data.json"
    data = requests.get(final_uri).json() \
                   .get("result", {}).get("pageContext", {}) \
                   .get("node", {}).get("data", {}).get("content", {})
    pic_url = "https://www.nationalgeographic.co.uk/photo-of-the-day/" \
        f"{year}/{month}?image="
    for p in data.get("images", []):
        purl = p["entity"]["mediaImage"]["url"]
        px = f"https://static.nationalgeographic.co.uk{purl}"
        pid = purl[purl.rindex("/")+1:purl.rindex(".")]
        pictures[px] = {
            "image": px,
            "copyright": "{} - {}".format(p["entity"]["mediaImage"]["title"],
                                          p["entity"]["credit"]),
            "url": pic_url + pid,
            "type": "National Geographic"
        }
    return pictures


def preferences():
    return {
        "name": "National Geographic"
    }
