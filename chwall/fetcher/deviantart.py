import requests
from lxml import html
from xml.etree import ElementTree


def fetch_pictures(config):
    collecs = config.get("deviantart", {}).get("collections", [])
    if len(collecs) == 0:
        return {}
    pictures = {}
    url = "https://backend.deviantart.com/rss.xml?type=deviation&q={}"
    for q in collecs:
        data = ElementTree.fromstring(requests.get(url.format(q)).text)
        for item in data[0].findall("item"):
            title = item.find("title").text
            author = item.find(
                        "{http://search.yahoo.com/mrss/}credit").text
            pic_page = item.find("link").text
            scrap = html.fromstring(requests.get(pic_page).text)
            meta = scrap.xpath('//meta[@property="og:image"]')[0]
            pic_data = meta.attrib.get("content").split("/v1/fill/")
            pic_url = pic_data[0]
            pictures[pic_url] = {
                "image": pic_url,
                "type": "Deviantart",
                "url": pic_page,
                "description": title,
                "author": author
            }
    return pictures


def preferences():
    return {
        "name": "Deviantart",
        "options": {
            "collections": {
                "widget": "list"
            }
        }
    }
