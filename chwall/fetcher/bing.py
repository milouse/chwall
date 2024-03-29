import re
from chwall.fetcher import requests_get

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    bing_conf = config.get("bing", {}).get("locales", [])
    if len(bing_conf) > 0:
        i18n_src = bing_conf
    else:
        i18n_src = ["en-US", "fr-FR"]
    pictures = {}
    already_done = []
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&n=8&mkt={}"
    for lang in i18n_src:
        lang_url = "{}[0-9]{{10}}".format(lang.upper())
        data = requests_get(url.format(lang)).json()
        for p in data["images"]:
            ad = re.sub(lang_url, "", p["url"])
            if ad in already_done:
                continue
            already_done.append(ad)
            px = "https://www.bing.com{}".format(p["url"])
            pictures[px] = {
                "image": px,
                "copyright": p["copyright"],
                "url": p["copyrightlink"],
                "type": "Bing"
            }
    return pictures


def preferences():
    return {
        "name": "Bing",
        "options": {
            "locales": {
                "widget": "list",
                "default": ["en-US", "fr-FR"],
                "label": _("Locales")
            }
        }
    }
