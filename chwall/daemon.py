#!/usr/bin/env python3

import os
import sys
import time
import signal
import subprocess

# chwall imports
from chwall.utils import BASE_CACHE_PATH, read_config
from chwall.wallpaper import pick_wallpaper, ChwallWallpaperSetError, \
                             current_wallpaper_info


import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext
_p = gettext.ngettext


class ChwallRestartTimer(Exception):
    """Exception raised in order to escape from a time.sleep()."""
    pass


def wait_before_change(sleep_time):
    with open("{}/last_change".format(BASE_CACHE_PATH), "w") as f:
        f.write(str(int(time.time())))
    try:
        time.sleep(sleep_time)
    except ChwallRestartTimer:
        wait_before_change(sleep_time)


def restart_sleep(_signo, _stack_frame):
    raise ChwallRestartTimer()


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def last_wallpaper_change():
    pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
    if not os.path.exists(pid_file):
        return -1
    with open("{}/last_change".format(BASE_CACHE_PATH), "r") as f:
        try:
            last_change = int(time.time()) - int(f.read().strip())
        except ValueError:
            last_change = -1
    return last_change


def daemon_change_label(last_change, next_change):
    last_change_label = None
    next_change_label = None
    if last_change > 60:
        last_change_m = int(last_change / 60)
        last_change_s = last_change % 60
        last_change_label = _p(
            "Last change was 1 minute and {seconds}s ago",
            "Last change was {minutes} minutes and {seconds}s ago",
            last_change_m).format(minutes=last_change_m,
                                  seconds=last_change_s)
    else:
        last_change_label = (_("Last change was {seconds}s ago")
                             .format(seconds=last_change))
    if next_change > 60:
        next_change_m = int(next_change / 60)
        next_change_s = next_change % 60
        next_change_label = _p(
            "Next change in 1 minute and {seconds}s",
            "Next change in {minutes} minutes and {seconds}s",
            next_change_m).format(minutes=next_change_m,
                                  seconds=next_change_s)
    else:
        next_change_label = (_("Next change in {seconds}s")
                             .format(seconds=next_change))
    return last_change_label, next_change_label


def daemon_info(config):
    last_change = -1
    next_change = -1
    daemon_state = "stopped"
    daemon_state_label = _("Daemon stopped")
    daemon_enabled = False
    daemon_type = "standalone"

    last_change = last_wallpaper_change()
    change_labels = (None, None)
    if last_change != -1:
        daemon_state = "started"
        daemon_state_label = _("Daemon started")
        sleep_time = config['general']['sleep']
        next_change = sleep_time - last_change
        change_labels = daemon_change_label(last_change, next_change)

    systemd_path = os.path.expanduser("~/.config/systemd/user")
    if os.path.exists("{}/chwall.service".format(systemd_path)):
        daemon_type = "systemd"
        if os.path.exists("{}/default.target.wants/chwall.service"
                          .format(systemd_path)):
            daemon_enabled = True
        else:
            daemon_state_label = _("{daemon_state} (disabled)").format(
                daemon_state=daemon_state_label)

    return {
        "last-change": last_change,
        "next-change": next_change,
        "last-change-label": change_labels[0],
        "next-change-label": change_labels[1],
        "daemon-state-label": daemon_state_label,
        "daemon-type": daemon_type,
        "daemon-enabled": daemon_enabled,
        "daemon-state": daemon_state
    }


def notify_daemon_if_any(sig=signal.SIGUSR1):
    pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
    if not os.path.exists(pid_file):
        return False
    pid = None
    with open(pid_file, "r") as f:
        pid = f.read().strip()
    if sig == signal.SIGTERM:
        print(_("Kill process {pid}").format(pid=pid))
    else:
        print(_("Sending process {pid} signal {sid}")
              .format(pid=pid, sid=sig))
    try:
        os.kill(int(pid), sig)
    except ValueError:
        return False
    return True


def notify_app_if_any():
    pid_data = subprocess.run(["pgrep", "-f", "chwall.+app"],
                              stdout=subprocess.PIPE)
    try:
        pid = int(pid_data.stdout.decode().strip())
    except ValueError:
        return False
    print(_("Sending process {pid} signal {sid}")
          .format(pid=pid, sid=signal.SIGUSR1))
    os.kill(pid, signal.SIGUSR1)
    return True


def show_notification():
    wallinfo = current_wallpaper_info()
    subprocess.run(["notify-send", "-a", "chwall", "-i",
                    wallinfo["local-picture-path"],
                    "Chwall - {}".format(wallinfo["type"]),
                    wallinfo["description"]])


def daemon_step():
    config = read_config()
    wait_before_change(config['general']['sleep'])
    # Config may have change during sleep
    config = read_config()
    try:
        pick_wallpaper(config)
        notify_app_if_any()
        if config["general"]["notify"] is True:
            show_notification()
    except ChwallWallpaperSetError:
        # weird, but try again after some sleep
        pass


def daemon_loop():
    error_code = 0
    try:
        signal.signal(signal.SIGTERM, kill_daemon)
        signal.signal(signal.SIGUSR1, restart_sleep)
        while True:
            daemon_step()
    except (KeyboardInterrupt, SystemExit):
        print(_("Exit signal received"))
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e), file=sys.stderr)
        error_code = 1
    finally:
        print(_("Cleaning up…"))
        os.unlink("{}/chwall_pid".format(BASE_CACHE_PATH))
        if error_code == 0:
            print("Kthxbye!")
        return error_code


def daemonize():
    """
    do the UNIX double-fork magic, see Stevens' "Advanced
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    https://web.archive.org/web/20131017130434/http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    newpid = os.fork()
    if newpid > 0:
        sys.exit(0)
    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
    # Fork a second time
    newpid = os.fork()
    if newpid > 0:
        sys.exit(0)


def start_daemon():
    if sys.argv[-1] != "-D":
        daemonize()
    with open("{}/chwall_pid".format(BASE_CACHE_PATH), "w") as f:
        f.write(str(os.getpid()))
    print(_("Start loop"))
    sys.exit(daemon_loop())


if __name__ == "__main__":
    start_daemon()
