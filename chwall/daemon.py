#!/usr/bin/env python3

import os
import sys
import time
import signal
import subprocess

# chwall imports
from chwall import __version__
from chwall.utils import BASE_CACHE_PATH, read_config, cleanup_cache, \
                         get_logger
from chwall.wallpaper import pick_wallpaper, ChwallWallpaperSetError, \
                             current_wallpaper_info


import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext

logger = get_logger(__name__)


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


def last_wallpaper_change(sleep_time):
    change_file = "{}/last_change".format(BASE_CACHE_PATH)
    if not os.path.exists(change_file):
        return -1
    with open(change_file, "r") as f:
        try:
            last_change = int(time.time()) - int(f.read().strip())
        except ValueError:
            last_change = -1
    if last_change > sleep_time:
        # We are currently reading a very old last_change flag file. Certainly
        # because the daemon has crashed without cleaning up its pid
        # file, or because we have just booted the computer.
        # Let’s assume it is stopped.
        return -1
    return last_change


def daemon_change_label(last_change, next_change):
    if last_change > 60:
        last_change_m = int(last_change / 60)
        last_change_s = last_change % 60
        last_change_label = gettext.ngettext(
            "Last change was {minutes} minute and {seconds}s ago",
            "Last change was {minutes} minutes and {seconds}s ago",
            last_change_m
        ).format(minutes=last_change_m, seconds=last_change_s)
    else:
        last_change_label = (_("Last change was {seconds}s ago")
                             .format(seconds=last_change))
    if next_change > 60:
        next_change_m = int(next_change / 60)
        next_change_s = next_change % 60
        next_change_label = gettext.ngettext(
            "Next change in {minutes} minute and {seconds}s",
            "Next change in {minutes} minutes and {seconds}s",
            next_change_m
        ).format(minutes=next_change_m, seconds=next_change_s)
    else:
        next_change_label = (_("Next change in {seconds}s")
                             .format(seconds=next_change))
    return last_change_label, next_change_label


def daemon_info():
    config = read_config()
    sleep_time = config["general"]["sleep"]
    last_change = -1
    next_change = -1
    daemon_state = "stopped"
    daemon_state_label = _("Daemon stopped")
    daemon_enabled = False
    daemon_type = "standalone"

    last_change = last_wallpaper_change(sleep_time)
    change_labels = (_("Daemon stopped"), _("Daemon stopped"))
    if last_change != -1:
        daemon_state = "started"
        daemon_state_label = _("Daemon started")
        next_change = sleep_time - last_change
        change_labels = daemon_change_label(last_change, next_change)

    systemd_path = os.path.expanduser("~/.config/systemd/user")
    if os.path.exists("{}/chwall.timer".format(systemd_path)):
        daemon_type = "systemd"
        if os.path.exists("{}/timers.target.wants/chwall.timer"
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
        logger.warning(_("Kill process {pid}").format(pid=pid))
    else:
        logger.debug(_("Sending process {pid} signal {sid}")
                     .format(pid=pid, sid=sig))
    try:
        os.kill(int(pid), sig)
    except ValueError:
        return False
    except ProcessLookupError:
        # Weird, pid_file is orphaned...
        os.unlink(pid_file)
        return False
    return True


def stop_daemon_if_any():
    notify_daemon_if_any(signal.SIGTERM)


def notify_app_if_any():
    pid_data = subprocess.run(
        ["pgrep", "-f", "chwall.+app"],
        capture_output=True, text=True
    )
    try:
        pid = int(pid_data.stdout.strip())
    except ValueError:
        return False
    logger.debug(_("Sending process {pid} signal {sid}")
                 .format(pid=pid, sid=signal.SIGUSR1))
    os.kill(pid, signal.SIGUSR1)
    return True


def show_notification():
    wallinfo = current_wallpaper_info()
    if wallinfo["type"] == "" or wallinfo["local-picture-path"] == "":
        return
    subprocess.run(["notify-send", "-a", "chwall", "-i",
                    wallinfo["local-picture-path"],
                    "Chwall - {}".format(wallinfo["type"]),
                    wallinfo["description"]])


def daemon_step():
    config = read_config()
    wait_before_change(config["general"]["sleep"])
    # Config may have change during sleep
    config = read_config()
    try:
        pick_wallpaper(config)
    except ChwallWallpaperSetError:
        # weird, but try again after some sleep
        return
    notify_app_if_any()
    if config["general"]["notify"] is True:
        show_notification()


def daemon_loop():
    error_code = 0
    try:
        signal.signal(signal.SIGTERM, kill_daemon)
        signal.signal(signal.SIGUSR1, restart_sleep)
        while True:
            daemon_step()
    except (KeyboardInterrupt, SystemExit):
        logger.warning(_("Exit signal received"))
    except Exception as e:
        logger.error("{}: {}".format(type(e).__name__, e))
        error_code = 1
    finally:
        logger.info(_("Cleaning up…"))
        pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
        if os.path.isfile(pid_file):
            os.unlink(pid_file)
        if error_code == 0:
            logger.info("Kthxbye!")
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
    logger.info(_("Starting Chwall Daemon v{version}…")
                .format(version=__version__))
    # Try to keep cache as clean as possible
    deleted = cleanup_cache()
    logger.info(gettext.ngettext(
        "{number} cache entry has been removed.",
        "{number} cache entries have been removed.",
        deleted
    ).format(number=deleted))
    sys.exit(daemon_loop())


if __name__ == "__main__":
    start_daemon()
