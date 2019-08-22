import os
import glob

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    pathes = config.get("local", {}).get("pathes", [])
    if len(pathes) == 0:
        return {}
    pictures = {}
    for path in pathes:
        path = os.path.expanduser(path)
        for ext in ["jpg", "jpeg", "png"]:
            for f in glob.iglob("{}/*.{}".format(path, ext),
                                recursive=True):
                pictures[f] = {
                    "image": f,
                    "type": "local",
                    "url": f,
                    "copyright": _("Local wallpaper")
                }
    return pictures


def preferences():
    return {
        "name": _("Local files"),
        "options": {
            "pathes": {
                "widget": "list",
                "label": _("Wallpaper repositories")
            }
        }
    }
