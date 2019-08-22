import os
import glob

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    if "local" not in config:
        return {}
    if "pathes" not in config["local"]:
        return {}
    pictures = {}
    for path in config["local"]["pathes"]:
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
