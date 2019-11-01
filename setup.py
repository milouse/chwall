#!/usr/bin/env python

import os
import setuptools
from chwall.utils import VERSION

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)),
          "requirements.txt")) as f:
    requirements = f.readlines()


setuptools.setup(
    name="chwall",
    version=VERSION,
    description="Wallpaper changer daemon and client",
    author="Étienne Deparis",
    author_email="etienne@depar.is",
    license="WTFPL",
    url="https://git.deparis.io/chwall",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: What The F*** Public License (WTFPL)",
        "Programming Language :: Python :: 3"
    ],
    keywords="wallpaper",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    entry_points={
        "gui_scripts": [
            "chwall-icon = chwall.gui.icon:start_icon",
            "chwall-app = chwall.gui.app:start_app"
        ],
        "console_scripts": [
            "chwall-daemon = chwall.daemon:start_daemon",
            "chwall = chwall.client:ChwallClient"
        ]
    })
