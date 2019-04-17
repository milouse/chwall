import re
import requests
from lxml import html
from xml.etree import ElementTree

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    if "flickr" in config and "tags" in config["flickr"]:
        tags = ",".join(list(map(lambda x: x.strip(),
                                 config["flickr"]["tags"])))
    else:
        return {}
    url = "https://api.flickr.com/services/feeds/photos_public.gne?" \
          "tagmode=any&tags={tags}&format=rss_200_enc".format(tags=tags)
    collecs = {}
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

        collecs[pic_url] = {
            "image": pic_url,
            "type": "flickr",
            "url": pic_page,
            "copyright": (_("{title} by {author} (on {source})")
                          .format(title=title, author=author,
                                  source="Flickr"))
        }
    return collecs


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
