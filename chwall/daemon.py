#!/usr/bin/env python3

import os
import sys
import time
import signal
import subprocess

# chwall imports
from chwall import __version__
from chwall.utils import BASE_CACHE_PATH, read_config, get_logger, \
                         detect_systemd, ServiceFileManager
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


def save_change_time():
    with open(f"{BASE_CACHE_PATH}/last_change", "w") as f:
        f.write(str(int(time.time())))


def wait_before_change(sleep_time):
    save_change_time()
    try:
        time.sleep(sleep_time)
    except ChwallRestartTimer:
        wait_before_change(sleep_time)


def restart_sleep(*args):
    raise ChwallRestartTimer()


def kill_daemon(*args):
    sys.exit(0)


def last_wallpaper_change(sleep_time):
    change_file = f"{BASE_CACHE_PATH}/last_change"
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
    seconds = last_change
    if seconds > 60:
        minutes = int(last_change / 60)
        seconds = last_change % 60
        last_change_label = gettext.ngettext(
            f"Last change was {minutes} minute and {seconds}s ago",
            f"Last change was {minutes} minutes and {seconds}s ago",
            minutes
        )
    else:
        last_change_label = _("Last change was {seconds}s ago")

    seconds = next_change
    if seconds > 60:
        minutes = int(next_change / 60)
        seconds = next_change % 60
        next_change_label = gettext.ngettext(
            f"Next change in {minutes} minute and {seconds}s",
            f"Next change in {minutes} minutes and {seconds}s",
            minutes
        )
    else:
        next_change_label = _(f"Next change in {seconds}s")

    return last_change_label, next_change_label


def daemon_info():
    config = read_config()
    sleep_time = config["general"]["sleep"]
    last_change = -1
    next_change = -1
    daemon_state = "stopped"
    daemon_state_label = _("Daemon stopped")

    last_change = last_wallpaper_change(sleep_time)
    change_labels = (_("Daemon stopped"), _("Daemon stopped"))
    if last_change != -1:
        daemon_state = "started"
        daemon_state_label = _("Daemon started")
        next_change = sleep_time - last_change
        change_labels = daemon_change_label(last_change, next_change)

    sfm = ServiceFileManager()
    service_file_status = sfm.service_file_status()
    if not service_file_status["enabled"]:
        daemon_state_label = _(f"{daemon_state_label} (disabled)")

    return {
        "last-change": last_change,
        "next-change": next_change,
        "last-change-label": change_labels[0],
        "next-change-label": change_labels[1],
        "daemon-state-label": daemon_state_label,
        "daemon-type": service_file_status["type"],
        "daemon-enabled": service_file_status["enabled"],
        "daemon-state": daemon_state
    }


def systemd_timer_running():
    if not detect_systemd():
        return False

    status = subprocess.run(
        ["systemctl", "--user", "-P", "ActiveState", "show",
         "chwall.timer"],
        check=True, capture_output=True, text=True
    ).stdout.strip()
    return status == "active"


def stop_systemd_timer():
    err = subprocess.run(
        ["systemctl", "--user", "stop", "chwall.timer"]
    ).returncode
    change_file = f"{BASE_CACHE_PATH}/last_change"
    if os.path.exists(change_file):
        os.unlink(change_file)
    return err


def restart_systemd_timer():
    err = subprocess.run(
        ["systemctl", "--user", "restart", "chwall.timer"]
    ).returncode
    return err == 0


def notify_daemon_if_any(action="notify"):
    if systemd_timer_running():
        if action == "stop":
            return stop_systemd_timer()

        save_change_time()

        if action == "notify":
            return restart_systemd_timer()
        return True

    pid_file = f"{BASE_CACHE_PATH}/chwall_pid"
    if not os.path.exists(pid_file):
        return False

    pid = None
    with open(pid_file, "r") as f:
        pid = f.read().strip()
    if not pid:
        return False

    if action == "stop":
        sid = signal.SIGTERM
        logger.warning(_(f"Kill process {pid}"))
    else:
        sid = signal.SIGUSR1
        logger.debug(_(f"Sending process {pid} signal {sid}"))
    try:
        os.kill(int(pid), sid)
    except ValueError:
        return False
    except ProcessLookupError:
        # Weird, pid_file is orphaned...
        os.unlink(pid_file)
        return False
    return True


def notify_app_if_any():
    pid_data = subprocess.run(
        ["pgrep", "-f", "chwall.+app"],
        capture_output=True, text=True
    )
    try:
        pid = int(pid_data.stdout.strip())
    except ValueError:
        return False
    sid = signal.SIGUSR1
    logger.debug(_(f"Sending process {pid} signal {sid}"))
    os.kill(pid, sid)
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
        pid_file = f"{BASE_CACHE_PATH}/chwall_pid"
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
    sfm = ServiceFileManager()
    if sfm.systemd_service_file_exists():
        save_change_time()
        return subprocess.run(
            ["systemctl", "--user", "start", "chwall.timer"]
        )

    if sys.argv[-1] != "-D":
        daemonize()
    with open(f"{BASE_CACHE_PATH}/chwall_pid", "w") as f:
        f.write(str(os.getpid()))
    logger.info(_("Starting Chwall Daemon v{version}…")
                .format(version=__version__))
    sys.exit(daemon_loop())


if __name__ == "__main__":
    start_daemon()
