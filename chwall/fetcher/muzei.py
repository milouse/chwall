import json
import datetime

from chwall.fetcher import requests_get


def fetch_pictures(config):
    today = datetime.date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1
    # We get the last month meta file to have enough wallpaper to show (~30).
    # As we don't have a mecanism to ensure today's wallpaper is displayed,
    # that's sufficient.
    metafile = f"{year}{month:0>2}.txt"
    baseuri = "https://storage.googleapis.com/muzeifeaturedart/archivemeta"
    rawdata = requests_get(f"{baseuri}/{metafile}").text
    # Only the first line is interesting
    data = json.loads(rawdata.split("\n", 1)[0])
    pictures = {}
    for pic in data:
        url = pic["thumb_url"].replace("lt-thumb", "lt-full")
        pictures[url] = {
            "image": url,
            "type": "muzei",
            "url": pic["details_url"],
            "description": pic["title"],
            "author": pic["byline"]
        }
    return pictures


def preferences():
    return {"name": "Muzei"}
