#!/usr/bin/env python3
"""Build a deterministic public ZIP; device identity is selected on installation."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import zipfile


def package(root, profile, dest):
    info = json.loads((profile / 'profile.json').read_text())
    for name, key in [('sony_g8ff.ko', 'module_sha256'), ('ff_test', 'ff_test_sha256')]:
        if hashlib.sha256((profile / name).read_bytes()).hexdigest() != info[key]:
            raise RuntimeError('Unvalidated binary: ' + name)
    data = {str(p.relative_to(root / 'module')): p.read_bytes() for p in (root / 'module').rglob('*') if p.is_file()}
    if 'config.sh' in data:
        raise RuntimeError('Private installation config must never be packaged')
    fields = {'G8FF_KERNEL': info['kernel_release'], 'G8FF_FINGERPRINT': info['fingerprint'], 'G8FF_SHA256': info['module_sha256'], 'G8FF_TEST_SHA256': info['ff_test_sha256']}
    data['profile.sh'] = ''.join(f'{k}={shlex.quote(v)}\n' for k,v in fields.items()).encode()
    for name in ['sony_g8ff.ko', 'ff_test']:
        data['bin/' + name] = (profile / name).read_bytes()
    data['LICENSE'] = (root / 'LICENSE').read_bytes()
    if 'disable' in data:
        raise RuntimeError('Fresh installs must not be disabled')
    data['skip_mount'] = b''
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_STORED, compresslevel=9) as z:
        for name, content in sorted(data.items()):
            item = zipfile.ZipInfo(name, (2026,1,1,0,0,0))
            item.compress_type = zipfile.ZIP_STORED
            item.create_system = 3
            item.external_attr = (0o100700 if name in ['bin/g8ffctl','bin/ff_test','action.sh'] else 0o100600) << 16
            z.writestr(item, content)
    return hashlib.sha256(dest.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', default='ruby-os2.0.8.0-umotwxm')
    version = dict(line.split('=', 1) for line in (root/'module/module.prop').read_text().splitlines() if '=' in line)['version']
    parser.add_argument('--output', type=Path, default=root / f'dist/xiaomi-controller-rumble-v{version}-ruby.zip')
    args = parser.parse_args()
    digest = package(root, root / 'profiles' / args.profile, args.output)
    args.output.with_name('SHA256SUMS').write_text(f'{digest}  {args.output.name}\n')
    print(digest, args.output)


if __name__ == '__main__':
    main()
