import re
import requests
from lxml import html
from xml.etree import ElementTree


def fetch_pictures(config):
    tag_list = config.get("flickr", {}).get("tags", [])
    if len(tag_list) == 0:
        return {}
    tags = ",".join(list(map(lambda x: x.strip(), tag_list)))
    url = "https://api.flickr.com/services/feeds/photos_public.gne?" \
          "tagmode=any&tags={tags}&format=rss_200_enc".format(tags=tags)
    pictures = {}
    data = ElementTree.fromstring(requests.get(url).text)
    for item in data[0].findall("item"):
        title = item.find("title").text
        author = item.find("{http://search.yahoo.com/mrss/}credit").text
        pic_page = item.find("link").text

        # Bigger is best
        for size in ["o", "k", "h"]:
            scrap = html.fromstring(requests.get(
                "{}sizes/{}/".format(pic_page, size)).text)
            pic_data = scrap.xpath('//div[@id="allsizes-photo"]/img')[0]
            pic_url = pic_data.attrib.get("src")
            if re.search("_{}\\.jpg$".format(size), pic_url) is not None:
                break

        pictures[pic_url] = {
            "image": pic_url,
            "type": "Flickr",
            "url": pic_page,
            "description": title,
            "author": author
        }
    return pictures


def preferences():
    return {
        "name": "Flickr",
        "options": {
            "tags": {
                "widget": "list",
                "default": ["colorful"]
            }
        }
    }
