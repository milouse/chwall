import os
from io import StringIO
from unittest import TestCase, mock

from chwall.utils import ServiceFileManager
from chwall.client import ChwallClient


original_exists = os.path.exists
def exists_side_effect(path):
    if path.startswith("/usr/bin/chwall"):
        return False
    elif path.endswith("/chwall.yml"):
        # Force default config to be used
        return False
    elif path.endswith("/chwall/pictures"):
        # Do not force create cache folders
        return True
    return original_exists(path)


@mock.patch("os.path.exists", side_effect=exists_side_effect)
@mock.patch("sys.stdout", new_callable=StringIO)
class TestLocalDesktopFiles(TestCase):
    def setUp(self):
        self.maxDiff = None
        # Force english locale
        os.environ["LANG"] = "en_US"

    def test_01_create_local_desktop_file(self, mock_stdout, _mock_path):
        with open("tests/proofs/local-app-desktop", "r") as f:
            result = f.read().format(path=os.getcwd())
        sfm = ServiceFileManager()
        sfm.generate_desktop_file("./locale", "print")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_02_create_local_desktop_file_from_client(self, mock_stdout, _mock_path):
        with open("tests/proofs/local-app-desktop", "r") as f:
            result = f.read().format(path=os.getcwd())
        try:
            os.environ["CHWALL_LOCALE_DIR"] = "./locale"
            ChwallClient(["desktop"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_03_create_local_systemd_service_file(self, mock_stdout, _mock_path):
        with open("tests/proofs/local-systemd-unit", "r") as f:
            result = f.read().format(path=os.getcwd())
        sfm = ServiceFileManager()
        sfm.systemd_service_file()
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_04_create_local_systemd_service_file_from_client(
            self, mock_stdout, _mock_path
    ):
        with open("tests/proofs/local-systemd-unit", "r") as f:
            result = f.read().format(path=os.getcwd())
        try:
            ChwallClient(["systemd"])
        except SystemExit:
            pass
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_05_create_local_xdg_autostart_icon_file(self, mock_stdout, _mock_path):
        with open("tests/proofs/local-xdg-icon", "r") as f:
            result = f.read().format(path=os.getcwd())
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("icon")
        self.assertEqual(mock_stdout.getvalue(), result)

    def test_06_create_local_xdg_autostart_daemon_file(self, mock_stdout, _mock_path):
        with open("tests/proofs/local-xdg-daemon", "r") as f:
            result = f.read().format(path=os.getcwd())
        sfm = ServiceFileManager()
        sfm.xdg_autostart_file("daemon")
        self.assertEqual(mock_stdout.getvalue(), result)
