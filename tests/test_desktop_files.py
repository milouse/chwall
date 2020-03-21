import os
from io import StringIO
import unittest
from unittest.mock import patch

from chwall.utils import ServiceFileManager
from chwall.gui.app import generate_desktop_file
from chwall.client import ChwallClient


@patch("sys.stdout", new_callable=StringIO)
class TestDesktopFiles(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_01_create_desktop_file(self, mock_stdout):
        with open("tests/proofs/app-desktop", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        generate_desktop_file("./locale", "print")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_02_create_desktop_file_from_client(self, mock_stdout):
        with open("tests/proofs/app-desktop", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        try:
            ChwallClient(["desktop", "print", "./locale"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_03_create_systemd_service_file(self, mock_stdout):
        with open("tests/proofs/systemd-unit", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        sfm = ServiceFileManager()
        sfm.systemd_service_file()
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_04_create_systemd_service_file_from_client(self, mock_stdout):
        with open("tests/proofs/systemd-unit", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        try:
            ChwallClient(["systemd"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_05_create_xdg_autostart_icon_file(self, mock_stdout):
        with open("tests/proofs/xdg-icon", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("icon", "TEST ICON", "TEST DESC")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_06_create_xdg_autostart_daemon_file(self, mock_stdout):
        with open("tests/proofs/xdg-daemon", "r") as f:
            result = f.read()
        os.environ["CHWALL_FAKE_INSTALL"] = "exists"
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("daemon", "TEST DAEMON", "TEST DESC")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_07_create_local_desktop_file(self, mock_stdout):
        with open("tests/proofs/local-app-desktop", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        generate_desktop_file("./locale", "print")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_08_create_local_desktop_file_from_client(self, mock_stdout):
        with open("tests/proofs/local-app-desktop", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        try:
            ChwallClient(["desktop", "print", "./locale"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_09_create_local_systemd_service_file(self, mock_stdout):
        with open("tests/proofs/local-systemd-unit", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        sfm = ServiceFileManager()
        sfm.systemd_service_file()
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_10_create_local_systemd_service_file_from_client(self, mock_stdout):
        with open("tests/proofs/local-systemd-unit", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        try:
            ChwallClient(["systemd"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_11_create_local_xdg_autostart_icon_file(self, mock_stdout):
        with open("tests/proofs/local-xdg-icon", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("icon", "TEST ICON", "TEST DESC")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_12_create_local_xdg_autostart_daemon_file(self, mock_stdout):
        with open("tests/proofs/local-xdg-daemon", "r") as f:
            result = f.read().format(path=os.getcwd())
        os.environ["CHWALL_FAKE_INSTALL"] = "absent"
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("daemon", "TEST DAEMON", "TEST DESC")
        self.assertEqual(mock_stdout.getvalue(), result)
