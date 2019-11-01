import re
import requests
from datetime import date
from xml.etree import ElementTree

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    pictures = {}
    conf = config.get("smashing", {})
    with_cal = conf.get("calendar", "without")
    curmonth_only = conf.get("current", False)
    feed = "https://www.smashingmagazine.com/category/wallpapers/index.xml"
    month_array = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
                   "sep", "oct", "nov", "dec"]
    if curmonth_only:
        tdy = date.today()
        month_re = "(?P<month>{month}-{year})".format(
            month=month_array[tdy.month - 1], year=(tdy.year - 2000)
        )
    else:
        month_re = "(?P<month>[a-z]{3}-[0-9]{2})"
    size_re = "(?P<size>[0-9]+x[0-9]+)"
    file_expr = re.compile(
        "href=\"(http://files\\.smashingmagazine\\.com/wallpapers/"
        "{month_re}/(?P<slug>[^/]+)/((?:no)?cal)/"
        "(?P=month)-(?P=slug)-(?:no)?cal-{size_re}\\.png)\" "
        "title=\"(.+) - (?P=size)\">(?P=size)<".format(
            month_re=month_re, size_re=size_re
        )
    )
    xml_data = ElementTree.fromstring(requests.get(feed).text)
    for item in xml_data[0].findall("item"):
        pic_page = item.find("link").text
        content = item.find(
            "{http://purl.org/rss/1.0/modules/content/}encoded").text
        pix_data = {}
        for match in file_expr.findall(content):
            if with_cal == "with" and match[3] == "nocal":
                continue
            if with_cal == "without" and match[3] == "cal":
                continue
            if match[2] not in pix_data:
                pix_data[match[2]] = {
                    "sizes": {},
                    "month": match[1],
                    "cal": match[3],
                    "title": match[5]
                }
            pix_data[match[2]]["sizes"][match[4]] = match[0]
        for slug, data in pix_data.items():
            sorted_width = sorted(
                data["sizes"].keys(),
                key=lambda x: int(x.split("x")[0]),
                reverse=True
            )
            month_data = data["month"].split("-")
            month_n = month_array.index(month_data[0]) + 1
            month_id = "{}-20{}".format(
                str(month_n).rjust(2, "0"), month_data[1]
            )
            url = data["sizes"][sorted_width[0]]
            pictures[url] = {
                "image": url,
                "type": "Smashing Magazine",
                "url": pic_page + "#{slug}-{month}".format(
                    slug=slug, month=month_id
                ),
                "copyright": data["title"]
            }
    return pictures


def preferences():
    return {
        "name": "Smashing Magazine",
        "options": {
            "calendar": {
                "label": _("Select wallpapers with or without calendar"),
                "widget": "select",
                "values": [
                    ("both", _("Both")),
                    ("with", _("With")),
                    ("without", _("Without"))
                ],
                "default": "without"
            },
            "current": {
                "label": _("Select only wallpapers for current month"),
                "widget": "toggle",
                "default": False
            }
        }
    }
