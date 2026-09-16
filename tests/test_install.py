import hashlib
import unittest
import zipfile
from support import Fixture, packager, ROOT, PROFILE

class InstallTests(unittest.TestCase):
    def setUp(self):self.f=Fixture();self.addCleanup(self.f.cleanup)
    def test_no_controller_installs_enabled_pending(self):
        r=self.f.install();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse((self.f.mod/'config.sh').exists());self.assertFalse((self.f.mod/'disable').exists())
        self.assertIn('setup is pending',r.stdout);self.assertTrue((self.f.mod/'install.boot').exists())
        self.assertFalse((self.f.tmp/'mutations').exists())
    def test_single_controller_all_manager_contracts(self):
        self.f.controller()
        for changes in ({'MAGISK_VER_CODE':'30700'},{'KSU':'true'},{'KSU':'true','KSUNEXT':'true'}):
            r=self.f.install(**changes);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn("G8FF_POLL='4'",(self.f.mod/'config.sh').read_text())
            self.assertNotIn('02:00:00:00:00:01',r.stdout)
            self.assertFalse((self.f.mod/'disable').exists())
    def test_multiple_controllers_install_pending(self):
        self.f.controller();self.f.controller('two','02:00:00:00:00:02')
        r=self.f.install();self.assertEqual(r.returncode,0);self.assertIn('Multiple',r.stdout)
        self.assertFalse((self.f.mod/'config.sh').exists())
    def test_unready_controller_does_not_delay_install(self):
        self.f.controller(poll=None,driver=None)
        r=self.f.install();self.assertEqual(r.returncode,0);self.assertIn('not ready',r.stdout)
        self.assertFalse((self.f.tmp/'ticks').exists());self.assertFalse((self.f.mod/'config.sh').exists())
    def test_bad_firmware_arch_recovery_rejected(self):
        for changes in ({'TEST_KERNEL':'bad'},{'TEST_ROM':'bad'},{'ARCH':'x64'},{'BOOTMODE':'false'}):
            self.assertEqual(self.f.install(**changes).returncode,17)
    def test_corrupt_driver_or_test_binary_rejected(self):
        for name in ['sony_g8ff.ko','ff_test']:
            p=self.f.mod/'bin'/name;data=p.read_bytes();p.write_bytes(b'bad')
            self.assertEqual(self.f.install().returncode,17);p.write_bytes(data)
    def test_migrate_v021_offline_preserves_disabled(self):
        old="G8FF_KERNEL=old\nG8FF_UNIQ='02:00:00:00:00:01'\nG8FF_POLL='4'\n"
        (self.f.old/'config.sh').write_text(old);(self.f.old/'disable').touch()
        r=self.f.install();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('settings retained',r.stdout);self.assertTrue((self.f.mod/'disable').exists())
        self.assertEqual((self.f.old/'config.sh').read_text(),old)
        self.assertNotIn('G8FF_KERNEL',(self.f.mod/'config.sh').read_text())
    def test_failed_upgrade_keeps_active_installation(self):
        p=self.f.old/'config.sh';p.write_text('existing');(self.f.old/'disable').touch()
        self.assertEqual(self.f.install(TEST_KERNEL='other').returncode,17)
        self.assertEqual(p.read_text(),'existing');self.assertTrue((self.f.old/'disable').exists())
    def test_old_config_is_not_executed_or_silently_retargeted(self):
        marker=self.f.tmp/'executed';(self.f.old/'config.sh').write_text('touch '+str(marker)+'\n')
        self.f.controller();r=self.f.install();self.assertEqual(r.returncode,0)
        self.assertFalse(marker.exists());self.assertFalse((self.f.mod/'config.sh').exists())
    def test_malformed_identity_and_poll_remain_pending(self):
        d=self.f.controller(uid="02:00:00:00:00:01\nHID_UNIQ='; touch BAD; #")
        self.assertEqual(self.f.install().returncode,0);self.assertFalse((self.f.mod/'config.sh').exists())
        (d/'uevent').write_text('HID_ID=0005:0000054C:000005C4\nHID_UNIQ=02:00:00:00:00:01\n')
        (d/'bt_poll_interval').write_text('63\n');self.assertEqual(self.f.install().returncode,0)
        self.assertFalse((self.f.mod/'config.sh').exists())
    def test_chinese_installation_text(self):
        r=self.f.install(TEST_LOCALE='zh-TW');self.assertIn('安裝完成，請重新開機一次',r.stdout)
    def test_reproducible_zip_no_disable_or_identity(self):
        other=self.f.tmp/'other.zip';packager.package(ROOT,PROFILE,other)
        self.assertEqual(self.f.zip.read_bytes(),other.read_bytes())
        with zipfile.ZipFile(self.f.zip) as z:
            for name in ['disable','config.sh','install.boot']:self.assertNotIn(name,z.namelist())
            self.assertIn('action.sh',z.namelist())
            self.assertEqual(hashlib.sha256(z.read('bin/sony_g8ff.ko')).hexdigest(),self.f.profile['module_sha256'])
