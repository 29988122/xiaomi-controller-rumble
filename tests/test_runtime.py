import os
import subprocess
import time
import unittest
from support import Fixture

class RuntimeTests(unittest.TestCase):
    def setUp(self):self.f=Fixture();self.addCleanup(self.f.cleanup)
    def prepare(self,connected=True):
        d=self.f.controller() if connected else None
        r=self.f.install();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.f.runtime();return d
    def test_pending_watch_never_loads_driver(self):
        self.prepare(False);r=self.f.ctl('watch');self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse((self.f.tmp/'mutations').exists())
    def test_deferred_setup_and_rumble_without_another_reboot(self):
        self.prepare(False);d=self.f.controller();r=self.f.ctl('action')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('No additional reboot',r.stdout);self.assertIn('confirm physical',r.stdout)
        self.assertEqual((self.f.tmp/'rumble-targets').read_text().strip(),str(self.f.dev/'event1'))
        self.assertEqual((self.f.mod/'config.sh').stat().st_mode&0o777,0o600)
        self.assertEqual((d/'driver').readlink().name,'sony_g8ff')
    def test_saved_controller_once_reboot_path_no_automatic_rumble(self):
        self.prepare();r=self.f.ctl('once');self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse((self.f.tmp/'rumble-targets').exists())
    def test_same_boot_action_and_staging_rejected(self):
        self.prepare();self.f.boot.write_text('boot-one\n')
        r=self.f.ctl('action');self.assertNotEqual(r.returncode,0);self.assertIn('Reboot once',r.stdout)
        self.f.boot.write_text('boot-two\n');(self.f.mod/'update').touch()
        self.assertNotEqual(self.f.ctl('action').returncode,0);self.assertFalse((self.f.tmp/'mutations').exists())
    def test_disabled_action_does_not_enable_itself(self):
        self.prepare();(self.f.mod/'disable').touch();r=self.f.ctl('action')
        self.assertNotEqual(r.returncode,0);self.assertTrue((self.f.mod/'disable').exists())
        self.assertFalse((self.f.tmp/'mutations').exists())
    def test_disabled_upgrade_enable_then_action_without_reboot(self):
        (self.f.old/'config.sh').write_text("G8FF_UNIQ='02:00:00:00:00:01'\nG8FF_POLL='4'\n")
        (self.f.old/'disable').touch();self.prepare();(self.f.mod/'disable').unlink()
        self.assertEqual(self.f.ctl('action').returncode,0)
    def test_other_controller_does_not_replace_saved_identity(self):
        d=self.prepare();old=(self.f.mod/'config.sh').read_bytes()
        (d/'uevent').write_text('HID_ID=0005:0000054C:000005C4\nHID_UNIQ=02:00:00:00:00:02\n')
        r=self.f.ctl('action');self.assertNotEqual(r.returncode,0);self.assertIn('different controller',r.stdout)
        self.assertEqual((self.f.mod/'config.sh').read_bytes(),old);self.assertFalse((self.f.tmp/'mutations').exists())
    def test_multiple_candidates_do_not_enroll(self):
        self.prepare(False);self.f.controller();self.f.controller('two','02:00:00:00:00:02')
        self.assertNotEqual(self.f.ctl('action').returncode,0);self.assertFalse((self.f.mod/'config.sh').exists())
    def test_late_probe_finishes_during_action(self):
        self.prepare(False);d=self.f.controller(poll=None,driver=None)
        hook=self.f.tmp/'tick.sh';hook.write_text('ln -s "'+str(self.f.sys/'bus/hid/drivers/sony')+'" "'+str(d/'driver')+'"\necho 4 > "'+str(d/'bt_poll_interval')+'"\n')
        r=self.f.ctl('action',TEST_TICK_SCRIPT=str(hook));self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_unbound_timeout_is_bounded_and_no_driver_loaded(self):
        self.prepare(False);self.f.controller(poll=None,driver=None)
        r=self.f.ctl('action');self.assertNotEqual(r.returncode,0);self.assertIn('not ready',r.stdout)
        self.assertEqual(len((self.f.tmp/'ticks').read_text().splitlines()),20)
        self.assertFalse((self.f.tmp/'mutations').exists())
    def test_target_change_during_setup_rejected(self):
        self.prepare(False);d=self.f.controller(poll=None)
        hook=self.f.tmp/'tick.sh';hook.write_text('echo "HID_ID=0005:0000054C:000005C4\nHID_UNIQ=02:00:00:00:00:02" > "'+str(d/'uevent')+'"\n')
        r=self.f.ctl('action',TEST_TICK_SCRIPT=str(hook));self.assertNotEqual(r.returncode,0)
        self.assertIn('changed',r.stdout);self.assertFalse((self.f.mod/'config.sh').exists())
    def test_binding_failure_restores_stock_and_reports_it(self):
        d=self.prepare();r=self.f.ctl('action',TEST_BIND_FAIL='sony_g8ff/bind')
        self.assertNotEqual(r.returncode,0,r.stdout+r.stderr);self.assertIn('stock driver was restored',r.stdout)
        self.assertEqual((d/'driver').readlink().name,'sony');self.assertFalse((self.f.sys/'module/sony_g8ff').exists())
    def test_stop_restores_driver_and_preserves_poll(self):
        d=self.prepare();self.assertEqual(self.f.ctl('action').returncode,0)
        r=self.f.ctl('stop');self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual((d/'driver').readlink().name,'sony');self.assertEqual((d/'bt_poll_interval').read_text(),'4')
    def test_stale_lock_files_do_not_block_action(self):
        self.prepare();(self.f.mod/'run').mkdir()
        for name in ['operation.lock','worker.lock','action.lock']:(self.f.mod/'run'/name).write_text('stale pid')
        self.assertEqual(self.f.ctl('action').returncode,0)
    def test_concurrent_actions_only_test_once(self):
        self.prepare();cmd=['sh',str(self.f.mod/'bin/g8ffctl'),'action']
        p=subprocess.Popen(cmd,env=dict(self.f.env,TEST_FF_SLEEP='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+5
            while not (self.f.tmp/'rumble-targets').exists() and time.monotonic()<deadline:time.sleep(.02)
            r=self.f.ctl('action');self.assertNotEqual(r.returncode,0);self.assertIn('Another action',r.stdout)
            out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,out+err)
            self.assertEqual(len((self.f.tmp/'rumble-targets').read_text().splitlines()),1)
        finally:
            if p.poll() is None:p.kill();p.wait()
    def test_rumble_only_uses_saved_controller(self):
        self.prepare();self.f.controller('two','02:00:00:00:00:02',event='event2')
        self.assertEqual(self.f.ctl('action').returncode,0)
        self.assertNotIn('event2',(self.f.tmp/'rumble-targets').read_text())
    def test_firmware_mismatch_never_loads(self):
        self.prepare();self.assertNotEqual(self.f.ctl('action',TEST_KERNEL='other').returncode,0)
        self.assertFalse((self.f.tmp/'mutations').exists())
