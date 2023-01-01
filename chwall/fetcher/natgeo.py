import requests
from lxml import html


def fetch_pictures(config):
    pictures = {}
    final_uri = "https://www.nationalgeographic.co.uk/page-data/photo-of-day/page-data.json"  # noqa
    images = requests.get(final_uri).json() \
                     .get("result", {}).get("pageContext", {}) \
                     .get("node", {}).get("data", {}).get("content", {}) \
                     .get("images", [])
    pic_url = "https://www.nationalgeographic.co.uk/photo-of-day?image="
    for p in images:
        entity = p["entity"]
        media = entity["mediaImage"]
        purl = media["url"]
        px = f"https://static.nationalgeographic.co.uk{purl}"
        pid = purl[purl.rindex("/")+1:purl.rindex(".")]
        description = []
        if media["title"] and media["title"] != "":
            description.append(media["title"])
        if media["alt"] and media["alt"] != "":
            description.append(media["alt"])
        if entity["caption"] and entity["caption"] != "":
            caption = html.fromstring(entity["caption"]).text
            if caption:
                description.append(caption)
        photographers = []
        for data in entity.get("photographers", []):
            author = data["entity"]["photographer"]["entity"]
            photographers.append(author["name"])
        if len(photographers) == 0:
            photographers = [entity["credit"]]
        pictures[px] = {
            "image": px,
            "description": " - ".join(description),
            "author": ", ".join(photographers),
            "url": pic_url + pid,
            "type": "National Geographic"
        }
    return pictures


def preferences():
    return {
        "name": "National Geographic"
    }
