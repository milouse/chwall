#!/usr/bin/env python3

import os
import sys
import time
import yaml
import signal
import tempfile


# chwall imports
from chwall.utils import BASE_CACHE_PATH, build_picture_lists, \
                         read_config
from chwall.wallpaper import choose_wallpaper


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def daemon_loop(temp_file, temp_info_file, config):
    sleep_time = config['general']['sleep']
    error_code = 0
    try:
        while True:
            choose_wallpaper(temp_file, config)
            time.sleep(sleep_time)
    except (KeyboardInterrupt, SystemExit):
        print("Kthxbye!")
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e), file=sys.stderr)
        error_code = 1
    finally:
        os.unlink(temp_file)
        os.unlink(temp_info_file)
        sys.exit(error_code)


def run_daemon(data, config):
    signal.signal(signal.SIGTERM, kill_daemon)
    f = tempfile.mkstemp(suffix="_chwall")
    with open(f[1], "w") as tmp:
        yaml.dump(data, tmp, explicit_start=True,
                  default_flow_style=False)
    os.close(f[0])
    temp_file = f[1]
    del f
    temp_info_file = "{}/temp".format(BASE_CACHE_PATH)
    with open(temp_info_file, "w") as f:
        f.write(temp_file)
    print("Start loop")
    newpid = os.fork()
    if newpid == 0:
        daemon_loop(temp_file, temp_info_file, config)


def daemon():
    config = read_config()
    data = build_picture_lists(config)
    run_daemon(data, config)


if __name__ == "__main__":
    daemon()
