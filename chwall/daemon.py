#!/usr/bin/env python3

import os
import sys
import time
import signal


# chwall imports
from chwall.utils import BASE_CACHE_PATH, read_config
from chwall.wallpaper import pick_wallpaper, ChwallWallpaperSetError


class ChwallRestartTimer(Exception):
    """Exception raised in order to escape from a time.sleep()."""
    pass


def wait_before_change(sleep_time):
    try:
        time.sleep(sleep_time)
    except ChwallRestartTimer:
        wait_before_change(sleep_time)


def restart_sleep(_signo, _stack_frame):
    raise ChwallRestartTimer()


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def notify_daemon_if_any(sig=signal.SIGUSR1):
    pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
    if not os.path.exists(pid_file):
        return False
    pid = None
    with open(pid_file, "r") as f:
        pid = f.read().strip()
    if sig == signal.SIGTERM:
        print("Kill process {}".format(pid))
    else:
        print("Sending process {} signal {}".format(pid, sig))
    try:
        os.kill(int(pid), sig)
    except ValueError:
        return False
    return True


def daemon_loop():
    config = read_config()
    sleep_time = config['general']['sleep']
    error_code = 0
    try:
        signal.signal(signal.SIGTERM, kill_daemon)
        signal.signal(signal.SIGUSR1, restart_sleep)
        while True:
            try:
                pick_wallpaper(config)
            except ChwallWallpaperSetError:
                # weird, but try again…
                continue
            # Sleep may be interrupted by a signal raising an error.
            # We should add an handler on signal.SIGALRM
            wait_before_change(sleep_time)
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
