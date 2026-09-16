# Xiaomi Controller Rumble

[繁體中文](README.zh-TW.md) · [Technical write-up](docs/writeup.md) · [Build / porting](docs/build-and-port.md)

Restore missing **Bluetooth controller force feedback** on a specifically validated Xiaomi/Redmi stock kernel, without replacing its boot image. This project publishes a working Redmi `ruby` case study, a firmware-specific driver, and a method for investigating other devices whose available kernel sources do not match the shipping firmware.

**The method is portable. The supplied `.ko` is not a universal Xiaomi driver.** Similar device age, Android version or a shared `4.19` prefix does not establish ABI compatibility. This concerns the controller's motors, not the phone's vibration motor.

## Supported profile

| Component | Verified case |
|---|---|
| Phone | Redmi Note 12 Pro 5G, `ruby`, model `22101316G` |
| ROM | HyperOS `OS2.0.8.0.UMOTWXM`, Android 14 |
| Kernel | `4.19.191-gdecc267868f3`, ARM64 |
| Controller | GameSir G8+, DS4 Bluetooth mode `054C:05C4` |
| Physical/runtime validation | Magisk Alpha 30700, private predecessor using the identical `.ko` |
| Public v0.2.1 installer | 18 automated tests; on-phone `customize.sh` check using installed Magisk helpers in a temporary directory; full manager install/activation not repeated |
| KernelSU / KernelSU Next | ZIP and script contract reviewed/tested; **no hardware validation** |
| Other root forks / phones / ROMs | Unverified; no matching profile means no install |

The stock Sony driver had `CONFIG_SONY_FF` disabled. The replacement `sony_g8ff` driver exposes standard `FF_RUMBLE`; Android then identifies the controller as a vibration-capable input device. A `.ko` runs in **kernel space**. The module's shell scripts run in userspace and manage loading, binding and recovery.

## Download and install

Download the firmware-specific ZIP and `SHA256SUMS` from [v0.2.1 prerelease](https://github.com/29988122/xiaomi-controller-rumble/releases/tag/v0.2.1). Identical assets are committed in [dist](dist/). The ZIP is shared by Magisk and KernelSU-family managers; compatible packaging does not make the embedded kernel binary compatible with a different kernel.

1. Check every row of the supported profile. Keep a working USB ADB recovery connection and a backup of your own boot image.
2. Connect exactly **one** DS4 Bluetooth controller with ID `054C:05C4`; wait for its normal inputs to initialize. G8+ is the physically tested controller. Disconnect other matching controllers.
3. Install from your running root manager. Recovery installation is unsupported. An unmatched kernel/ROM, a damaged driver, zero/multiple matching controllers or incomplete controller initialization aborts installation.
4. Installation stores the selected controller's unique ID **only on your phone** and leaves the module **disabled**. Reboot to finish installation, review the profile/recovery instructions, enable it in the manager, then reboot to activate.
5. The controller will be rebound after boot and reconnects. Existing Bluetooth polling is retained rather than reset to a tuning preset.

No network request or telemetry is made by the installed module. It does not mount or replace `/system`; no mounting metamodule or Zygisk is required for this module. Existing module ID `sony_g8ff_ruby` is retained to avoid installing a second watcher alongside the private predecessor. An update re-selects the single currently connected controller and starts disabled again.

### If installation fails

v0.2.1 distinguishes no controller, multiple controllers, unsupported driver and incomplete Sony initialization. For one valid controller, it waits up to 20 seconds for driver readiness without loading or rebinding a driver.

If `[controller:unbound]` or `[controller:initializing]` appears, fully power the controller off/on, reconnect in DS4 mode, confirm normal inputs work and retry. Bluetooth can show “connected” even when the kernel driver failed to initialize. On the reported phone, the kernel logged `Failed to get calibration data from Dualshock 4` followed by `failed to claim input`; after reconnection it bound to `sony` normally with 4 ms polling. The underlying cause of that failed calibration exchange is unknown. This installer update does not bypass calibration or repair a persistently failing controller handshake.

See [v0.2.1 changes and validation](CHANGELOG.md). The firmware-specific `.ko` is unchanged.

### Check, stop and recover

From a root shell:

```sh
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl status
```

To disable immediately and prevent next-boot activation:

```sh
touch /data/adb/modules/sony_g8ff_ruby/disable
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl stop
```

The manager's disable switch followed by a reboot is another recovery path. `stop` ends this module's worker, rebinds the selected controller to stock `sony`, and unloads `sony_g8ff`. See the root manager's recovery documentation if Android cannot finish booting: [Magisk](https://topjohnwu.github.io/Magisk/faq.html), [KernelSU](https://kernelsu.org/guide/rescue-from-bootloop.html).

After a ROM/kernel update the guard refuses unmatched versions. Do not edit the guard or vermagic to force compatibility; build and validate a new profile. Moving to a KernelSU-patched kernel can also require a new profile, even on the same phone.

## What was actually verified

- The owner confirmed both motors with raw HID output and again through kernel `FF_RUMBLE`.
- Android exposed a vibrator input mapper. Three consecutive Bluetooth reconnections passed after fixing a probe-initialization race.
- Screen doze (`Dozing`) → wake (`Awake`), reboot autoload, disable-to-stock and re-enable were checked. This is not a deep-suspend endurance test.
- Polling remained 4 ms in the tested setup; stock boot-image hash was unchanged. SELinux, CFI and MODVERSIONS were not disabled.
- The original driver input interfaces remained present. **Steam Link, in-game controls/latency and a 30-minute game session were not tested**, at the owner's request. On this setup Low Latency Video had already been disabled to address a separate latency issue.
- The `.ko` rebuilt byte-for-byte identically. All 61 required export CRCs matched independently built evidence; 624 computed exports matched stock. These checks complement, not replace, runtime testing.

The detailed [English](docs/writeup.md) / [繁體中文](docs/writeup.zh-TW.md) write-up explains the successful path, failed probes, nine reconstructed enum entries and what this evidence does **not** prove.

## Development and contributions

```sh
python3 -m pip install pyelftools==0.33
python3 -m unittest discover -s tests -v
python3 tools/package.py
```

See [build and porting](docs/build-and-port.md) for pinned source/toolchain downloads, Linux-container commands, ABI gates and adding a profile. Firmware profiles separate version assumptions and artifacts from the common installer; the existing build/export layout remains a **ruby ARM64 case-study implementation**, not an automatic kernel reverse-engineering tool.

For an [issue](https://github.com/29988122/xiaomi-controller-rumble/issues), include device codename, ROM fingerprint, kernel release, controller mode/VID:PID, root-manager version, phase of failure and a minimal redacted log. Do not upload boot images, device addresses, serials or full system dumps. A new-profile contribution needs independently computed ABI evidence and temporary-load/recovery results before being advertised as supported. Prefer a draft report if no safe runtime test is available.

## Credits and license

Project and physical test coordination: [29988122](https://github.com/29988122), with AI-assisted investigation, implementation and documentation. Physical motor confirmation came from the owner; software checks alone were not counted as physical validation. No claim of inventing Linux force feedback or being the first to rebind a driver is made.

The driver is derived from [Xiaomi's published Sony HID driver](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/914ba8403bb3a957ed37b99dcecdbafce9d16121/drivers/hid/hid-sony.c), retaining its upstream copyright/license notices. New project code is GPL-2.0-or-later; individual imported files retain their notices. See [LICENSE](LICENSE) and [source provenance](docs/build-and-port.md#provenance).
