import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT/'profiles/ruby-os2.0.8.0-umotwxm'
spec = importlib.util.spec_from_file_location('packager', ROOT/'tools/package.py')
packager = importlib.util.module_from_spec(spec); spec.loader.exec_module(packager)

class Fixture:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(); self.tmp=Path(self.temp.name)
        self.mod=self.tmp/'module';self.zip=self.tmp/'module.zip'
        packager.package(ROOT,PROFILE,self.zip)
        with zipfile.ZipFile(self.zip) as z:z.extractall(self.mod)
        self.sys=self.tmp/'sys';self.adb=self.tmp/'adb';self.dev=self.tmp/'dev/input';self.dev.mkdir(parents=True)
        self.devices=self.sys/'bus/hid/devices';self.devices.mkdir(parents=True)
        self.old=self.adb/'modules/sony_g8ff_ruby';self.old.mkdir(parents=True)
        self.boot=self.tmp/'boot';self.boot.write_text('boot-one\n')
        for p in self.mod.rglob('*'):
            if p.is_file() and (p.suffix=='.sh' or p.name=='g8ffctl'):
                text=p.read_text().replace('/proc/sys/kernel/random/boot_id',str(self.boot)).replace('/sys/',str(self.sys)+'/').replace('/data/adb/',str(self.adb)+'/').replace('/dev/input/',str(self.dev)+'/')
                if p.name=='g8ffctl':
                    text=text.replace("kernel_write() { printf '%s' \"$2\" > \"$1\"; }",'kernel_write() { kernel_write_mock "$1" "$2"; }').replace('[ -c "$G8FF_EVENT" ]','[ -f "$G8FF_EVENT" ]')
                p.write_text(text)
        self.cmd=self.tmp/'commands';self.cmd.mkdir()
        self.profile=json.loads((PROFILE/'profile.json').read_text())
        self.env=dict(os.environ,PATH=str(self.cmd)+os.pathsep+os.environ['PATH'],MODPATH=str(self.mod),BOOTMODE='true',ARCH='arm64',TEST_KERNEL=self.profile['kernel_release'],TEST_ROM=self.profile['fingerprint'],TEST_SYS=str(self.sys),TEST_TMP=str(self.tmp),TEST_DEV=str(self.dev),TEST_LOCALE='en-US')
        self.shell('uname','echo "$TEST_KERNEL"')
        self.shell('getprop','case "$1" in ro.build.fingerprint) echo "$TEST_ROM";; *locale) echo "$TEST_LOCALE";; sys.boot_completed) echo 1;; esac')
        self.shell('sleep','echo tick >> "$TEST_TMP/ticks"; if [ -n "${TEST_TICK_SCRIPT:-}" ]; then sh "$TEST_TICK_SCRIPT"; fi; '+sys.executable+' -c "import time;time.sleep(0.02)"')
        self.python('flock','''import fcntl,sys
try: fcntl.flock(int(sys.argv[-1]),fcntl.LOCK_UN if '-u' in sys.argv else fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:sys.exit(1)
''')
        self.python('setsid','''import os,sys
os.setsid()
with open(os.environ['TEST_TMP']+'/workers','a') as f:f.write(str(os.getpid())+'\\n')
os.execvp(sys.argv[1],sys.argv[1:])
''')
        self.python('insmod','''import os,sys
from pathlib import Path
s=Path(os.environ['TEST_SYS'])/'module/sony_g8ff/parameters';s.mkdir(parents=True,exist_ok=True)
(s/'target_uniq').write_text(sys.argv[2].split('=',1)[1])
with open(os.environ['TEST_TMP']+'/mutations','a') as f:f.write('insmod\\n')
''')
        self.python('rmmod','''import os,shutil
from pathlib import Path
shutil.rmtree(Path(os.environ['TEST_SYS'])/'module/sony_g8ff')
with open(os.environ['TEST_TMP']+'/mutations','a') as f:f.write('rmmod\\n')
''')
        self.python('kernel_write_mock','''import os,sys
from pathlib import Path
p=Path(sys.argv[1]);s=Path(os.environ['TEST_SYS']);d=s/'bus/hid/devices'/sys.argv[2]
with open(os.environ['TEST_TMP']+'/mutations','a') as f:f.write(p.parent.name+'/'+p.name+' '+sys.argv[2]+'\\n')
if os.environ.get('TEST_BIND_FAIL')==p.parent.name+'/'+p.name:sys.exit(1)
if p.name=='unbind':(d/'driver').unlink(missing_ok=True)
else:
 (d/'driver').unlink(missing_ok=True);(d/'driver').symlink_to(p.parent)
''')
        # Fake FF device is independent of kernel operation mocks and records the exact target.
        self.shell('ff_fixture','echo "$1" >> "$TEST_TMP/rumble-targets"; '+sys.executable+' -c "import os,time;time.sleep(float(os.environ.get(\'TEST_FF_SLEEP\',\'0\')))"; test -f "$1"')
        self.runner=self.tmp/'installer.sh'
        self.runner.write_text('''abort() { echo "ABORT: $*"; exit 17; }
ui_print() { echo "$*"; }
set_perm_recursive() { :; }
set_perm() { :; }
. "$MODPATH/customize.sh"
''')
    def shell(self,name,body):
        p=self.cmd/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o700)
    def python(self,name,body):
        p=self.cmd/name;p.write_text('#!'+sys.executable+'\n'+body);p.chmod(0o700)
    def controller(self,name='0005:054C:05C4.0001',uid='02:00:00:00:00:01',poll='4',driver='sony',event='event1'):
        d=self.devices/name;d.mkdir()
        (d/'uevent').write_text('HID_ID=0005:0000054C:000005C4\nHID_UNIQ='+uid+'\n')
        if driver:(d/'driver').symlink_to(self.sys/'bus/hid/drivers'/driver)
        if poll is not None:(d/'bt_poll_interval').write_text(poll+'\n')
        i=d/'input/input1';(i/'capabilities').mkdir(parents=True);(i/'capabilities/ff').write_text('10000 0\n');(i/event).mkdir();(self.dev/event).touch()
        return d
    def install(self,**changes):
        return subprocess.run(['sh',str(self.runner)],env=dict(self.env,**changes),capture_output=True,text=True,timeout=10)
    def runtime(self):
        # Leave the public ZIP untouched; substitute executable only in the simulated phone.
        (self.mod/'bin/ff_test').write_bytes((self.cmd/'ff_fixture').read_bytes());(self.mod/'bin/ff_test').chmod(0o700)
        p=self.mod/'profile.sh';lines=p.read_text().splitlines();digest=hashlib.sha256((self.mod/'bin/ff_test').read_bytes()).hexdigest()
        p.write_text('\n'.join('G8FF_TEST_SHA256='+digest if x.startswith('G8FF_TEST_SHA256=') else x for x in lines)+'\n')
        self.boot.write_text('boot-two\n')
    def ctl(self,command,**changes):
        return subprocess.run(['sh',str(self.mod/'bin/g8ffctl'),command],env=dict(self.env,**changes),capture_output=True,text=True,timeout=10)
    def cleanup(self):
        workers=self.tmp/'workers'
        if workers.exists():
            for pid in workers.read_text().splitlines():
                try:os.killpg(int(pid),signal.SIGTERM)
                except ProcessLookupError:pass
            time.sleep(.05)
        self.temp.cleanup()
