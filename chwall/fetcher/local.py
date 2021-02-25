import os
import glob

from chwall.utils import get_logger

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext

logger = get_logger(__name__)


def fetch_pictures(config):
    conf = config.get("local", {})
    paths = conf.get("paths", [])
    include_fav = conf.get("favorites", True)
    fav_dir = config["general"]["favorites_path"]
    try:
        if os.path.exists(fav_dir) and include_fav:
            paths.insert(0, fav_dir)
    except PermissionError as e:
        logger.error(e)
    if len(paths) == 0:
        return {}
    pictures = {}
    for path in paths:
        path = os.path.expanduser(path)
        try:
            for ext in ["jpg", "jpeg", "png"]:
                glob_path = "{}/*.{}".format(path, ext)
                for f in glob.iglob(glob_path, recursive=True):
                    pictures[f] = {
                        "image": f,
                        "type": "local",
                        "url": f,
                        "copyright": _("Local wallpaper")
                    }
        except PermissionError as e:
            logger.error(e)
    return pictures


def preferences():
    return {
        "name": _("Local files"),
        "options": {
            "paths": {
                "widget": "list",
                "label": _("Wallpaper repositories")
            },
            "favorites": {
                "label": _("Include favorites wallpapers"),
                "widget": "toggle",
                "default": True
            }
        }
    }
