import re

from chwall.fetcher import requests_get

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def fetch_pictures(config):
    subreds = config.get("reddit", {}).get(
        "subreddits", ["wallpaper", "wallpapers", "EarthPorn"]
    )
    if len(subreds) == 0:
        return {}
    pictures = {}
    url = "https://www.reddit.com/r/{}.json?raw_json=1".format(
        "+".join(list(map(lambda x: x.strip(), subreds))))
    uagent = "python:Chwall:v{version} (by /u/milouse; https://git.umaneti.net/chwall)"  # noqa
    data = requests_get(url, uagent).json()
    collecs = data.get("data", {}).get("children", [])
    for p in collecs:
        if p["data"].get("post_hint") != "image":
            continue
        px = p["data"].get("url")
        if px is None:
            continue
        title = re.sub(r"\[[^]]*\]", "", p["data"]["title"]).strip()
        if len(title) > 200:
            title = title[0:200] + "…"
        desc = _("{title}, picked on {subreddit}").format(
            title=title, subreddit=p["data"]["subreddit_name_prefixed"])
        pictures[px] = {
            "image": px,
            "description": desc,
            "author": p["data"]["author"],
            "url": "https://www.reddit.com" + p["data"]["permalink"],
            "type": "Reddit"
        }
    return pictures


def preferences():
    return {
        "name": _("Fetcher for Reddit"),
        "options": {
            "subreddits": {
                "widget": "list",
                "default": ["wallpaper", "wallpapers", "EarthPorn"]
            }
        }
    }
