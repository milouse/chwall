import os

from chwall.fetcher import requests_get
from chwall.utils import get_logger

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext

logger = get_logger(__name__)


def fetch_pictures(config):
    wa_conf = config.get("wikiart", {})
    access_key = wa_conf.get("access_key")
    if access_key is None:
        logger.error(
            _("An ‘access_key’ param is required to fetch pictures "
              "from Wikiart.")
        )
        return {}
    secret_key = wa_conf.get("secret_key")
    if secret_key is None:
        logger.error(
            _("A ‘secret_key’ param is required to fetch pictures "
              "from Wikiart.")
        )
        return {}
    locale = wa_conf.get("locale", "en")
    base_uri = f"https://www.wikiart.org/{locale}/Api/2/"
    log_data = requests_get(
        f"{base_uri}login",
        params={"accessCode": access_key, "secretCode": secret_key}
    ).json()
    session_key = log_data.get("SessionKey")
    if session_key is None:
        logger.error(
            _("An error occured while authenticating your credentials "
              "with Wikiart. Please check again your access and secret "
              "keys.")
        )
    query = wa_conf.get("query")
    payload = {
        "authSessionKey": session_key,
        "imageFormat": "HD"
    }
    endpoint = "MostViewedPaintings"
    if query is not None and query != "":
        endpoint = "PaintingSearch"
        payload["term"] = query
    data = requests_get(f"{base_uri}{endpoint}", params=payload).json()
    pictures = {}
    for pic in data["data"]:
        url = pic["image"]
        if pic["url"] is None:
            basename = os.path.basename(url)
            pic["url"] = os.path.splitext(basename.split("!", 1)[0])[0]
        pictures[url] = {
            "image": url,
            "type": "wikiart",
            "url": "https://www.wikiart.org/{}/{}/{}".format(
                locale, pic["artistUrl"], pic["url"]
            ),
            "description": pic["title"],
            "author": pic["artistName"]
        }
    return pictures


def preferences():
    return {
        "name": "Wikiart",
        "options": {
            "access_key": {
                "widget": "text",
                "label": _("API access key")
            },
            "secret_key": {
                "widget": "text",
                "label": _("API secret key")
            },
            "locale": {
                "widget": "select",
                "values": [
                    ("en", "English"),
                    ("ru", "Русский"),
                    ("es", "Español"),
                    ("uk", "Українська"),
                    ("fr", "Français"),
                    ("it", "Italiano"),
                    ("pt", "Portuguese"),
                    ("de", "Deutsch"),
                    ("zh", "中文")
                ],
                "default": "en",
                "label": _("Locales")
            },
            "query": {
                "widget": "text",
                "label": _("Search query")
            }
        }
    }
