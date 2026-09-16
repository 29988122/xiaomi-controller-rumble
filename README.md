# Xiaomi Controller Rumble

[繁體中文](README.zh-TW.md) · [Technical write-up](docs/writeup.md) · [Build / porting](docs/build-and-port.md) · [Changelog](CHANGELOG.md)

Restore missing Bluetooth controller rumble on one validated Redmi firmware using a replacement Sony HID driver. The phone's boot image stays unchanged. **The included driver is firmware-specific; the investigation method can be adapted to other devices.** This restores the controller's motors.

## Download and install

Download [v0.3.0 preview](https://github.com/29988122/xiaomi-controller-rumble/releases/tag/v0.3.0) and its `SHA256SUMS`. [dist](dist/) contains identical files.

1. Check the compatibility table below. Install the ZIP from Magisk or a compatible KernelSU-family manager; do not extract it.
2. **Reboot once.** Fresh installations are enabled automatically.
3. If one supported controller was connected and ready during installation, it is already saved. Otherwise connect your G8+ in DS4 Bluetooth mode, leaving only that supported controller connected.
4. Press the module's **Action** button to finish setup or check it. It sends a short test: left once, right twice. Confirm that you feel the rumble. **No second reboot is needed.**

The controller can be absent, still initializing or one of several connected controllers during installation. Installation still completes in **setup pending** state. No replacement driver is loaded until a controller has been saved and is ready. The background service never chooses an unsaved controller by itself.

The Action button waits up to 20 seconds for initialization. If it still fails, fully power the controller off/on, reconnect in DS4 mode and press Action again. Bluetooth “connected” alone does not prove that the Sony driver finished initialization. The module does not toggle Bluetooth or bypass failed calibration.

**v0.3.0's installer, Action and service lifecycle have not been tested on a real phone.** This preview is delivered with automated tests at the owner's request. The kernel `.ko` is identical to the previously physically tested driver; that evidence does not validate the new workflow. Keep USB ADB and your own recovery method available.

## Compatibility

| Component | Scope |
|---|---|
| Phone | Redmi Note 12 Pro 5G, `ruby`, `22101316G` |
| ROM | HyperOS `OS2.0.8.0.UMOTWXM`, Android 14 |
| Kernel | `4.19.191-gdecc267868f3`, ARM64 |
| Controller | GameSir G8+, DS4 Bluetooth `054C:05C4` |
| Historical driver hardware validation | Magisk Alpha 30700, predecessor using identical `.ko` |
| v0.3.0 workflow | Simulated installation/runtime tests; **no phone installation, reboot or physical Action test** |
| KernelSU / Next | Common ZIP/script contracts; **no hardware validation** |
| Other phones, firmware or protocols | Unsupported by this binary |

Nintendo, Xbox and Steam Controller protocols are not added by this release. A similar Android/kernel version does not establish compatibility. Installing a KernelSU-patched kernel can invalidate this profile even on the same phone.

This ZIP does not mount `/system`; it needs no mounting metamodule or Zygisk. Use a current manager with an Action button and BusyBox `flock` / `setsid`. Magisk 30.7 is the shell-compatibility baseline. There is no network request or telemetry. The selected controller identity stays on the phone.

## Updating and everyday use

- Update by installing the newer ZIP under the same module ID, `sony_g8ff_ruby`, then reboot once. Valid saved settings are preserved even if the controller is offline.
- A previously disabled module remains disabled. After the update reboot, enable its switch and press Action to start; no further reboot is needed.
- Pressing Action while an installation/update still needs a reboot shows that next step rather than launching staged code.
- Boot and reconnection are silent: no automatic motor tests. Only Action triggers the short test.
- A different controller never replaces the saved one automatically. This version has no controller-switching UI.
- Chinese system locales receive Traditional Chinese messages; other locales receive English.

## Disable and recover

Turn off the module in your root manager. The running service attempts to restore the stock Sony driver after any in-flight test ends. If the controller does not recover, disconnect/reconnect it or reboot with the module disabled.

For root-shell diagnostics:

```sh
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl status
```

To stop now and prevent next-boot activation:

```sh
touch /data/adb/modules/sony_g8ff_ruby/disable
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl stop
```

ROM/kernel mismatches block activation. Never edit the checks or vermagic to force installation. See [Magisk recovery](https://topjohnwu.github.io/Magisk/faq.html) / [KernelSU recovery](https://kernelsu.org/guide/rescue-from-bootloop.html).

## What the evidence establishes

The predecessor's owner confirmed both motors through raw HID and standard FF. Three Bluetooth reconnects, screen doze/wake, reboot loading and disable-to-stock were checked. Boot hash was unchanged; SELinux, CFI and MODVERSIONS remained enforced. This was not a deep-suspend endurance test. Steam Link, in-game controls/latency and a 30-minute game session remain untested.

v0.3.0 keeps that `.ko` but changes the installation/service scripts and user-space FF test helper. The helper now verifies the opened input device's identity before sending effects, protecting against recycled event numbers. It has a reproducible cross-build and a QEMU rejection check; its new identity check has not been exercised against physical hardware.

Automated tests simulate deferred setup, migration, disabled states, disconnects, concurrent actions/workers and recovery. CI also checks scripts using Magisk's actual x86_64 BusyBox shell and `flock`; sysfs and manager installation helpers are still simulated. These tests do not boot Android or establish manager end-to-end success. See [build / validation](docs/build-and-port.md).

## Development and contributions

```sh
python3 -m pip install pyelftools==0.33
python3 -m unittest discover -s tests -v
python3 tools/package.py
```

See the [English](docs/writeup.md) / [中文](docs/writeup.zh-TW.md) investigation and [porting guide](docs/build-and-port.md). The driver matched 61 required symbol CRCs with independently computed evidence; 624 computed exports matched stock. CRCs are supporting evidence, not universal ABI proof.

[Report an issue](https://github.com/29988122/xiaomi-controller-rumble/issues) with device/ROM/kernel, controller mode, manager version and a minimal redacted error log. Exclude serials, Bluetooth addresses, boot images and full system dumps. New profiles need their own build/ABI and runtime evidence.

## Credits and license

Project and physical test coordination: [29988122](https://github.com/29988122), with AI-assisted investigation, implementation and documentation. Physical motor confirmation came from the owner. No claim of inventing Linux force feedback is made.

The driver derives from [Xiaomi's Sony HID source](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/914ba8403bb3a957ed37b99dcecdbafce9d16121/drivers/hid/hid-sony.c), retaining upstream notices. New project code is GPL-2.0-or-later; imported files retain their licenses. See [LICENSE](LICENSE) and [provenance](docs/build-and-port.md#provenance).
