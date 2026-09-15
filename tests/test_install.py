import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'profiles/ruby-os2.0.8.0-umotwxm'
spec = importlib.util.spec_from_file_location('packager', ROOT/'tools/package.py')
packager = importlib.util.module_from_spec(spec); spec.loader.exec_module(packager)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.zip = self.tmp/'module.zip'
        packager.package(ROOT, PROFILE, self.zip)
        self.mod = self.tmp/'module'
        with zipfile.ZipFile(self.zip) as z:z.extractall(self.mod)
        self.sys = self.tmp/'sys'
        self.devices = self.sys/'bus/hid/devices'; self.devices.mkdir(parents=True)
        p=self.mod/'lib/target.sh'; p.write_text(p.read_text().replace('/sys/',str(self.sys)+'/'))
        self.commands=self.tmp/'commands'; self.commands.mkdir()
        self.profile=json.loads((PROFILE/'profile.json').read_text())
        for name,body in {'uname':'printf "%s\\n" "$TEST_KERNEL"', 'getprop':'printf "%s\\n" "$TEST_ROM"'}.items():
            p=self.commands/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o700)
        self.env=dict(os.environ, PATH=str(self.commands)+os.pathsep+os.environ['PATH'], MODPATH=str(self.mod), BOOTMODE='true', ARCH='arm64',TEST_KERNEL=self.profile['kernel_release'],TEST_ROM=self.profile['fingerprint'])
        self.runner=self.tmp/'installer.sh'
        self.runner.write_text('''#!/bin/sh
abort() { echo "ABORT: $*"; exit 17; }
ui_print() { echo "$*"; }
# Installer API contract stubs: tests never chown/chcon host files.
set_perm_recursive() { :; }
set_perm() { :; }
. "$MODPATH/customize.sh"
''')
    def controller(self,name='one',uid='02:00:00:00:00:01',poll='4'):
        d=self.devices/name;d.mkdir()
        (d/'uevent').write_text('HID_ID=0005:0000054C:000005C4\nHID_UNIQ='+uid+'\n')
        (d/'driver').symlink_to(self.tmp/'sony')
        if poll is not None:(d/'bt_poll_interval').write_text(poll+'\n')
        return d
    def install(self,**changes):
        return subprocess.run(['sh',str(self.runner)],env=dict(self.env,**changes),capture_output=True,text=True,timeout=5)
    def test_zero_and_multiple_controllers_rejected(self):
        self.assertEqual(self.install().returncode,17)
        self.controller();self.controller('two','02:00:00:00:00:02')
        self.assertEqual(self.install().returncode,17)
        self.assertFalse((self.mod/'config.sh').exists())
    def test_single_controller_all_manager_contracts(self):
        self.controller()
        for env in ({'MAGISK_VER_CODE':'30700'},{'KSU':'true','KSU_VER_CODE':'13000'},{'KSU':'true','KSU_VER_CODE':'33000','KSUNEXT':'true'}):
            with self.subTest(env=env):
                r=self.install(**env);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                config=(self.mod/'config.sh').read_text()
                self.assertIn("G8FF_UNIQ='02:00:00:00:00:01'",config)
                self.assertIn("G8FF_POLL='4'",config)
                self.assertTrue((self.mod/'disable').is_file())
                self.assertTrue((self.mod/'skip_mount').is_file())
                self.assertNotIn('02:00:00:00:00:01',r.stdout)
    def test_firmware_arch_and_recovery_rejected(self):
        self.controller()
        for env in ({'TEST_KERNEL':'other'},{'TEST_ROM':'other'},{'ARCH':'x64'},{'BOOTMODE':'false'}):
            with self.subTest(env=env):self.assertEqual(self.install(**env).returncode,17)
    def test_corrupt_driver_rejected(self):
        self.controller();(self.mod/'bin/sony_g8ff.ko').write_bytes(b'corrupt')
        self.assertEqual(self.install().returncode,17)
    def test_unready_controller_rejected(self):
        self.controller(poll=None);self.assertEqual(self.install().returncode,17)
    def test_metadata_is_not_executed(self):
        self.controller(uid="'; touch BAD; #")
        self.assertEqual(self.install().returncode,17)
        self.assertFalse((self.mod/'config.sh').exists())
    def test_out_of_range_poll_rejected(self):
        self.controller(poll='63');self.assertEqual(self.install().returncode,17)
    def test_reproducible_zip_no_identity(self):
        other=self.tmp/'other.zip';packager.package(ROOT,PROFILE,other)
        self.assertEqual(self.zip.read_bytes(),other.read_bytes())
        with zipfile.ZipFile(self.zip) as z:
            self.assertNotIn('config.sh',z.namelist())
            self.assertNotIn(b'G8FF_UNIQ=',z.read('profile.sh'))
            self.assertEqual(hashlib.sha256(z.read('bin/sony_g8ff.ko')).hexdigest(),self.profile['module_sha256'])

if __name__ == '__main__':unittest.main()
