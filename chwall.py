#!/usr/bin/env python3

import sys

# chwall imports
from chwall.client import run_client
from chwall.daemon import run_daemon
from chwall.wallpaper import fetch_wallpaper, set_wallpaper
from chwall.utils import read_config, build_picture_lists


if __name__ == "__main__":
    config = read_config()

    if len(sys.argv) > 1 and sys.argv[1] != "once":
        run_client(config)
    # Daemon client will directly exits when done. Thus if we are here,
    # we only have to set wallpaper once or start the daemon

    data = build_picture_lists(config)

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        wp = fetch_wallpaper(data)
        set_wallpaper(wp[0], config)
    else:
        run_daemon(data, config)
