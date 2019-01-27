#!/usr/bin/env python3

import os
import glob


def fetch_pictures(config):
    if "local" not in config:
        return {}
    collecs = {}
    for path in config["local"]:
        path = os.path.expanduser(path)
        for ext in ["jpg", "jpeg", "png"]:
            for f in glob.iglob("{}/*.{}".format(path, ext),
                                recursive=True):
                collecs[f] = {
                    "image": f,
                    "type": "local",
                    "url": f,
                    "copyright": "Local wallpaper"
                }
    return collecs
