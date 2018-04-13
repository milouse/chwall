#!/usr/bin/env python3

import os
import sys
import time
import yaml
import signal
import tempfile


# chwall imports
from chwall.utils import BASE_CACHE_PATH, read_config
from chwall.wallpaper import build_wallpapers_list, choose_wallpaper


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def daemon_loop(road_map, config):
    sleep_time = config['general']['sleep']
    error_code = 0
    try:
        signal.signal(signal.SIGTERM, kill_daemon)
        while True:
            choose_wallpaper(road_map, config)
            time.sleep(sleep_time)
    except (KeyboardInterrupt, SystemExit):
        print("Kthxbye!")
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e), file=sys.stderr)
        error_code = 1
    finally:
        os.unlink(road_map)
        os.unlink("{}/roadmap".format(BASE_CACHE_PATH))
        sys.exit(error_code)


def daemon():
    config = read_config()
    data = build_wallpapers_list(config)
    f = tempfile.mkstemp(suffix="_chwall")
    with open(f[1], "w") as tmp:
        yaml.dump(data, tmp, explicit_start=True,
                  default_flow_style=False)
    os.close(f[0])
    road_map = f[1]
    del f
    with open("{}/roadmap".format(BASE_CACHE_PATH), "w") as f:
        f.write(road_map)
    print("Start loop")
    newpid = os.fork()
    if newpid == 0:
        daemon_loop(road_map, config)


if __name__ == "__main__":
    daemon()
