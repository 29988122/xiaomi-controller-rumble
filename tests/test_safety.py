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
