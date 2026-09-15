import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


device = load("device")
abi = load("verify_abi")


class SafetyTests(unittest.TestCase):
    def test_hotplug_waits_for_stock_probe_attributes(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            module = tmp / "module"
            (module / "bin").mkdir(parents=True)
            fake_sys = tmp / "sys"
            # Redirect sysfs only in this test copy; production has no override.
            script = (root / "module/bin/g8ffctl").read_text().replace("/sys/", str(fake_sys) + "/")
            (module / "bin/g8ffctl").write_text(script)
            (module / "config.sh").write_text("G8FF_KERNEL=test\nG8FF_FINGERPRINT=test\nG8FF_SHA256=test\nG8FF_UNIQ=test-device\nG8FF_POLL=4\n")
            params = fake_sys / "module/sony_g8ff/parameters"
            params.mkdir(parents=True)
            (params / "target_uniq").write_text("test-device\n")
            device_path = fake_sys / "bus/hid/devices/0005:054C:05C4.0001"
            device_path.mkdir(parents=True)
            (device_path / "uevent").write_text("HID_ID=0005:0000054C:000005C4\nHID_UNIQ=test-device\n")
            drivers = fake_sys / "bus/hid/drivers"
            for name in ("sony", "sony_g8ff"):
                (drivers / name).mkdir(parents=True)
                for operation in ("bind", "unbind"):
                    (drivers / name / operation).touch()
            (device_path / "driver").symlink_to(drivers / "sony")
            mocks = tmp / "commands"
            mocks.mkdir()
            for name in ("uname", "getprop", "sha256sum"):
                (mocks / name).write_text("#!/bin/sh\necho test\n")
                (mocks / name).chmod(0o700)
            env = dict(os.environ, PATH=str(mocks) + os.pathsep + os.environ["PATH"])
            command = ["sh", str(module / "bin/g8ffctl"), "once"]
            early = subprocess.run(command, env=env, capture_output=True, timeout=5)
            self.assertEqual(early.returncode, 0, early.stderr)
            self.assertEqual((drivers / "sony/unbind").read_text(), "")
            (device_path / "bt_poll_interval").write_text("4\n")
            ready = subprocess.run(command, env=env, capture_output=True, timeout=5)
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertEqual((drivers / "sony/unbind").read_text(), device_path.name)
            self.assertEqual((drivers / "sony_g8ff/bind").read_text(), device_path.name)
            self.assertEqual((device_path / "bt_poll_interval").read_text(), "4")

    def test_loader_rejects_incompatible_or_disabled_package(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            module = tmp / "module"
            (module / "bin").mkdir(parents=True)
            shutil.copy2(root / "module/bin/g8ffctl", module / "bin/g8ffctl")
            mocks = tmp / "commands"
            mocks.mkdir()
            for name, text in {"uname": "echo valid-kernel", "getprop": "echo valid-rom", "sha256sum": "echo valid-hash file", "insmod": 'touch "$G8FF_TEST_MARKER"'}.items():
                script = mocks / name
                script.write_text("#!/bin/sh\n" + text + "\n")
                script.chmod(0o700)
            env = dict(os.environ, PATH=str(mocks) + os.pathsep + os.environ["PATH"], G8FF_TEST_MARKER=str(tmp / "loaded"))
            valid = {"G8FF_KERNEL": "valid-kernel", "G8FF_FINGERPRINT": "valid-rom", "G8FF_SHA256": "valid-hash", "G8FF_UNIQ": "test-device", "G8FF_POLL": "4"}
            for field in ("G8FF_KERNEL", "G8FF_FINGERPRINT", "G8FF_SHA256", "disable"):
                settings = dict(valid)
                if field == "disable":
                    (module / "disable").touch()
                else:
                    settings[field] = "invalid"
                (module / "config.sh").write_text("".join(f"{k}={v}\n" for k, v in settings.items()))
                run = subprocess.run(["sh", str(module / "bin/g8ffctl"), "once"], env=env, capture_output=True, timeout=5)
                self.assertNotEqual(run.returncode, 0, field)
                self.assertFalse((tmp / "loaded").exists(), field)

    def test_complete_abi_required(self):
        stock = {"module_layout": {"crc": "0x01"}, "input_ff_create_memless": {"crc": "0x02"}}
        self.assertTrue(abi.compare(["input_ff_create_memless"], stock, stock)["passed"])
        self.assertFalse(abi.compare(["input_ff_create_memless"], stock, {})["passed"])
        self.assertFalse(abi.compare([], stock, stock)["passed"])
        wrong = dict(stock, input_ff_create_memless={"crc": "0x03"})
        self.assertFalse(abi.compare(["input_ff_create_memless"], stock, wrong)["passed"])
        self.assertFalse(abi.compare(["unknown"], stock, stock)["passed"])

    def test_bounded_motor_packet(self):
        packet = device.report(80, 0, 4)
        self.assertEqual(len(packet), 78)
        self.assertEqual(packet[:4], b"\x11\xc4\x00\x01")
        self.assertEqual(packet[6:8], b"\x00\x50")
        self.assertEqual(packet[8:74], bytes(66))
        # Independent bitwise CRC check, including Bluetooth output prefix.
        crc = 0xFFFFFFFF
        for byte in b"\xa2" + packet[:74]:
            crc ^= byte
            for _ in range(8):
                crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        self.assertEqual(packet[74:], (crc ^ 0xFFFFFFFF).to_bytes(4, "little"))
        self.assertEqual(device.report(0, 0, 4)[6:8], bytes(2))
        for values in [(81, 0, 4), (0, 255, 4), (0, 0, 63), (0, 0, 0)]:
            with self.assertRaises(ValueError):
                device.report(*values)


if __name__ == "__main__":
    unittest.main()
