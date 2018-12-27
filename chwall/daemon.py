#!/usr/bin/env python3

import os
import sys
import time
import signal


# chwall imports
from chwall.utils import BASE_CACHE_PATH, read_config
from chwall.wallpaper import pick_wallpaper, ChwallWallpaperSetError


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def daemon_loop():
    config = read_config()
    sleep_time = config['general']['sleep']
    error_code = 0
    try:
        signal.signal(signal.SIGTERM, kill_daemon)
        while True:
            try:
                pick_wallpaper(config)
            except ChwallWallpaperSetError:
                # weird, but try again…
                continue
            time.sleep(sleep_time)
    except (KeyboardInterrupt, SystemExit):
        print("Exit signal received")
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e), file=sys.stderr)
        error_code = 1
    finally:
        print("Cleaning up…")
        os.unlink("{}/chwall_pid".format(BASE_CACHE_PATH))
        if error_code == 0:
            print("Kthxbye!")
        return error_code


def daemon():
    newpid = os.fork()
    if newpid != 0:
        print("Start loop")
        return 0
    # In the forked process
    with open("{}/chwall_pid".format(BASE_CACHE_PATH), "w") as f:
        f.write(str(os.getpid()))
    return daemon_loop()


if __name__ == "__main__":
    sys.exit(daemon())
