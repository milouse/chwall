#!/usr/bin/env python3

import sys

# chwall imports
from chwall.client import run_client
from chwall.daemon import daemon
from chwall.gui.icon import start_icon
from chwall.gui.app import start_app, generate_desktop_file


if __name__ == "__main__":
    action = "daemon"
    if len(sys.argv) > 1:
        action = sys.argv[1]
    if action == "icon":
        start_icon()
    elif action in ["app", "gui"]:
        start_app()
    elif action == "desktop":
        generate_desktop_file(sys.argv[2])
    elif action != "daemon":
        run_client()
    else:
        sys.exit(daemon())
