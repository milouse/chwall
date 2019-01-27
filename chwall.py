#!/usr/bin/env python3

import sys

# chwall imports
from chwall.client import client
from chwall.daemon import daemon
from chwall.icon import start_icon


if __name__ == "__main__":
    action = "daemon"
    if len(sys.argv) > 1:
        action = sys.argv[1]
    if action in ["icon", "gui"]:
        start_icon()
    elif action != "daemon":
        sys.exit(client())
    else:
        sys.exit(daemon())
