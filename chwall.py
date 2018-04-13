#!/usr/bin/env python3

import sys

# chwall imports
from chwall.client import client
from chwall.daemon import daemon


if __name__ == "__main__":
    if len(sys.argv) > 1:
        client()
        sys.exit()
    daemon()
