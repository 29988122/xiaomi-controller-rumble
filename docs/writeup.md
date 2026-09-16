# Recovering controller rumble when the available kernel source does not match the phone

> v0.3.0 adds one-reboot installation and deferred setup through Action. The kernel driver is unchanged; the new service and FF helper are software-tested only. See [current instructions](../README.md) and [validation limits](../CHANGELOG.md).

> Follow-up: v0.2.1 fixes installer readiness waiting and diagnostic messages after a real calibration failure. See [the changelog](../CHANGELOG.md) for the narrower on-phone installer check. The original investigation below describes v0.2.0.

[繁體中文](writeup.zh-TW.md) · [Project README](../README.md)

## 1. A controller that worked, except for its motors

A GameSir G8+ connected to a Redmi Note 12 Pro 5G (`ruby`) in DS4 Bluetooth mode. Buttons and sticks were exposed, but controller rumble was missing. The phone ran Android 14 / HyperOS `OS2.0.8.0.UMOTWXM`, with kernel `4.19.191-gdecc267868f3` and Magisk Alpha. A separate streaming-latency investigation had already led the owner to disable Low Latency Video. We kept that setting; rumble repair was a different task.

The useful starting point was not the root-manager brand. It was the actual input path:

```text
Bluetooth HID -> built-in Sony driver -> Linux input device -> Android input framework
```

The G8+ presented Bluetooth VID:PID `054C:05C4` and was bound to `sony`. `/proc/config.gz` showed `CONFIG_HID_SONY=y` and `CONFIG_INPUT_FF_MEMLESS=y`, but `CONFIG_SONY_FF` was not set. The controller input node lacked `EV_FF` / `FF_RUMBLE`. This identified a compiled-out driver feature, rather than an Android setting that root could toggle.

**We do not know why Xiaomi shipped that configuration.** We observed the configuration and behavior, not the manufacturer's decision process. Likewise, the problem was a mismatch between publicly available source and this running firmware; this investigation does not establish the source-release status of every Xiaomi device.

## 2. Prove the physical output path first

Before risking a replacement kernel driver, we used the existing `hidraw` interface to send bounded, low-strength output to the selected controller. DS4 Bluetooth output is not the same as USB output: the test used a 78-byte report with ID `0x11`, the existing Bluetooth report interval, motor-update flags and a CRC32 covering the output prefix `0xA2` plus the first 74 report bytes. Motor values were capped at 80/255, with explicit stop commands and shell exit/signal cleanup.

The raw test requested one pulse on one motor and two on the other. A successful `write()` only proves that bytes were accepted by a software interface. The owner initially missed the sequence, so it was repeated; the owner then confirmed both sides vibrated. This established that this controller and the phone's built-in Bluetooth path could carry the output protocol. It did not yet prove Android's standard force-feedback path worked.

`tools/device.py` includes this diagnostic with exact-identity selection. Input event and hidraw numbers can change on every reconnect: resolve identity each time rather than hardcoding `/dev/input/event9` or `/dev/hidraw0`.

## 3. What replaces what — and where it runs

The fix is a separately compiled Sony-based driver named `sony_g8ff`. Its own compilation unit enables `CONFIG_SONY_FF`; the surrounding kernel already has the common memoryless FF implementation it needs. The new driver registers under a different name and refuses any device except the explicitly selected Bluetooth identity and supported VID:PID.

```text
userspace root-manager service
  -> load sony_g8ff.ko
  -> unbind selected HID device from sony
  -> bind that device to sony_g8ff

kernel FF request -> sony_g8ff -> Bluetooth HID output -> controller motors
```

A `.ko` is **kernel-space code**, not a userspace driver. Magisk/KernelSU scripts perform orchestration from userspace. The built-in Sony driver is not erased or unloaded: it remains available for other devices and for rollback. This works only when the relevant bus/driver supports unbinding and rebinding and an actually compatible module can be loaded.

The driver preserves the existing Sony input implementation, including the main input node, touchpad, motion sensors, battery and light interfaces. It sends a stop report during removal. The supervisor preserves the existing Bluetooth polling interval and restores the stock binding when disabled. This is a device-specific driver replacement, not a patch that edits the running kernel's configuration flag.

## 4. Building against a source tree that was close, but not identical

The public `ruby-s-oss` tree was an older Android 12-era release. Treating its release number as proof of compatibility would have been a mistake. The phone enabled MODVERSIONS, CFI and LTO; its compiler was Android Clang 11 r383902. We used that exact compiler family/build, in Linux x86_64, to generate ARM64 output.

The build host was chosen for tool compatibility: the matching prebuilt compiler executes on Linux x86_64, while the local Mac was macOS ARM64. A Linux VM on the Mac could also have worked. A task-specific rootless container made the existing Linux host convenient, with CPU/memory limits and no dependency installation into its host OS.

### Recover evidence from the running firmware

We made a read-only backup of the active boot partition, checked its hash against the phone, extracted the kernel and used `vmlinux-to-elf` to reconstruct an ELF symbol view. Reconstruction helps analyze existing bytes; it does not recover the manufacturer's missing C source.

For this **particular ARM64 kernel**, the export table had 16-byte absolute entries and a corresponding 4-byte CRC table. The extractor checked table bounds, symbol/name associations and counts before producing 12,380 exported-symbol records. Other kernel versions can use relative entries or different layouts. The bundled extractor is intentionally a case-study implementation and rejects unexpected layouts; do not apply its offsets blindly.

Live `/proc/kallsyms` addresses were masked. The investigation did not disable that protection; the local boot backup provided the evidence instead.

### The first ABI probe was misleading

An early probe placed many exported declarations in one translation unit and ran version generation. It produced apparent disagreements because type visibility in that synthetic translation unit differed from the real exporting source files. A generated CRC is only meaningful in its actual build context.

The corrected approach compiled the **real source files that implement and export the functions**, then collected their emitted `.symversions`. This changed the question from “can I make the declarations look plausible?” to “does this source/configuration independently describe the same exported interfaces as the shipping kernel?”

The actual driver imports initially matched except for three power-supply interfaces. Rather than copy stock CRC values into a mismatching build, we investigated the mismatch.

### Nine missing enum entries

The stock binary's `power_supply_attrs` array contained 284 properties; the available header described 275. The attribute names and ordering provided evidence for nine additional enum entries:

- `ADAPTING_POWER` after `MTBF_TEST`.
- `BATT_SN`, `MAX_LIFE_VOL`, `MAX_LIFE_TEMP`, `OVER_VOL_DURATION` after `THERMAL_LIMIT_FCC`.
- `FG_BATT_SN`, `FG_MAX_LIFE_VOL`, `FG_MAX_LIFE_TEMP`, `FG_OVER_VOL_DURATION` after `SHUTDOWN_DELAY`.

We checked the stock attribute array's layout and common callbacks, then applied this narrow **build-header** correction. It changed neither the phone's power-supply code nor its boot image. Some old enum names and sysfs names were already aliases; those were not renamed merely to make strings look alike.

After rebuilding the real export implementations, the three CRCs matched:

| Export | Independently matching CRC |
|---|---|
| `devm_power_supply_register` | `0xf0588502` |
| `power_supply_get_drvdata` | `0xaf625b30` |
| `power_supply_powers` | `0x5cfe9ca7` |

This allowed battery support to remain intact. It is evidence for those interfaces, **not a reconstruction of the entire missing vendor tree**.

### Verify the final object, not just the first imports

The build independently computed 624 exported interfaces that matched stock. The final `.ko` needed 61, including `module_layout`; all matched. Final linking can add compiler-generated dependencies, so checking only a pre-LTO object would miss part of the dependency set.

We checked the final ELF's architecture, exact imported-symbol coverage, every embedded `__versions` record, vermagic and CFI symbols. The kernel release suffix was applied through Kbuild after interface checks, not patched into a binary to bypass the loader. Rebuilding produced an identical module hash:

`4798bdc9521a0e68f63f5d430ab71122355f891aaf920aec9e01ecdcc4b09035`

MODVERSIONS CRCs are not a complete semantic or memory-safety proof. Inline behavior, configuration-dependent assumptions, internal structures, compiler instrumentation and runtime lifetimes still matter. Same-version strings alone are weaker evidence still. The temporary-load and rollback tests were therefore essential.

## 5. Temporary deployment exposed two useful mistakes

First, we loaded the module without any boot-time service, rebound only the selected controller, and inspected the resulting input capabilities. Android exposed a vibrator input mapper. A freestanding ARM64 evdev tester uploaded a bounded `FF_RUMBLE`, played it, stopped it and erased it. The owner again confirmed both motors physically vibrated. The final tester checks the stop and erase return values as well as upload/play.

Stock rollback was verified before persistence: rebind to `sony`, unload the replacement, observe FF disappear; reload and rebind, observe FF return.

The reconnect supervisor then exposed a race. A HID directory and `sony` driver link can exist before probe has finished creating `bt_poll_interval`. Treating that missing file as a permanent failure stopped the worker. The corrected worker waits until the stock driver's attributes are ready before attempting takeover. A regression test exercises this incomplete-probe state.

A separate test-harness issue came from requesting Bluetooth enable while disable was still transitioning. Waiting for complete state transitions avoided confusing an adapter lifecycle race with a driver failure. Software success labels were required in the captured output rather than relying solely on an ADB/shell exit status that could be obscured by cleanup commands.

After correction, three consecutive actual Bluetooth disconnect/reconnect cycles passed with the replacement binding, FF operations and the original 4 ms interval.

## 6. Persistence and honest validation boundaries

The module service waits for Android boot completion, checks the firmware and module hash, loads the driver and watches for reconnections. A lock prevents duplicate workers; boot identity allows a stale lock from a previous boot to be discarded. A disabled module restores the original binding and unloads the replacement.

USB ADB was verified before testing boot-time loading. A real reboot proved autoload and automatic binding. Disabling the installed module restored stock behavior; re-enabling restored FF. The boot image hash was unchanged, and SELinux remained enforcing. No CFI failure, unknown-symbol error, oops or panic was found in the final captured kernel log.

Screen doze-to-wake was checked, but this was not a deep-suspend stress test. Existing input interfaces were observed, but that is not equivalent to exercising every button, sensor and application. **Steam Link, gameplay latency and a 30-minute game session were explicitly skipped at the owner's request.** Android exposing FF support is a prerequisite, not proof that every game streams rumble correctly.

The public v0.2.0 ZIP contains the identical driver but a revised installer that selects exactly one connected controller and stores its identity locally. This public installer has automated contract tests. The phone keeps its previously validated installation; we did not reinstall the public wrapper or switch root managers to create a compatibility claim. KernelSU and KernelSU Next support the required package/script interfaces, but no KernelSU hardware validation was performed. Other forks remain unverified.

## 7. A workflow another person or AI agent can use

1. **Record the actual baseline.** Device codename, complete ROM fingerprint, kernel release/compiler/config, root mechanism, HID identity/binding and FF capabilities. Back up the active boot image privately and verify its hash. Do not infer the active slot from a filename guess.
2. **Prove the physical protocol.** Identify Bluetooth versus USB framing, bound motor strength/duration, issue stops and obtain physical confirmation. A transport write is not a motor test.
3. **Check feasibility before building.** Module loading/unloading, signature policy, required exported functions, FF dependencies, CFI/LTO, exact toolchain and unbind/rebind support all matter.
4. **Obtain the closest defensible sources and real firmware evidence.** Prefer a matching vendor release. Recover only narrowly justified differences when the evidence supports it; record every assumption.
5. **Compare independently.** Build the real exporting units, compare required versions, inspect the final module and reject unexplained mismatches. Do not copy expected CRCs into objects that did not compute them.
6. **Test temporarily.** No autoload for the first test. Select one device, preserve its interval, verify normal interfaces and standard FF, and test stock rollback.
7. **Then validate lifecycle.** Reconnect repeatedly, sleep/wake, application behavior, long sessions, disable/uninstall and reboot. Record what was skipped. Require a working recovery route before persistence.
8. **Publish a bounded profile.** Source and toolchain provenance, checksums, configuration, ABI evidence and real test scope. Share methods; do not advertise untested phones as supported.

An AI agent should keep a ledger of observation versus inference and ask the owner for physical outcomes. It should stop at an unresolved compatibility gate rather than treating root access as authorization to invent a passing result.

## 8. When this method is not enough

| Condition | Appropriate next step |
|---|---|
| Kernel cannot load modules, or required signatures cannot be supplied | Seek a properly built/signed kernel or a supported firmware path; this ZIP cannot override the policy. |
| Missing exports or FF dependencies | Determine whether a separately buildable dependency exists; otherwise a broader kernel change may be necessary. |
| Sources cannot justify required layouts/CFI assumptions | Obtain a matching source/build environment or stop deployment. |
| Device cannot be rebound safely | Investigate another driver integration strategy; do not assume every built-in driver is replaceable. |
| Raw rumble works, but FF/app behavior fails | Diagnose the input/framework/application path independently rather than repeatedly changing Bluetooth packets. |
| Considering a userspace bridge | `hidraw` plus a virtual input device may be an alternative where supported, but routing input and FF, avoiding duplicates, preserving sensors and Android recognition are substantial work. It is not implemented here. |

A complete matching kernel rebuild remains a valid route when matching sources, a proven build and recovery are available. A replacement module reduces the scope of the change; it does not remove the need for compatibility evidence. The lesson is to narrow uncertainty until a specific intervention is defensible, not to force arbitrary modules onto an opaque kernel.

## References

- [Pinned Xiaomi Sony driver](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/914ba8403bb3a957ed37b99dcecdbafce9d16121/drivers/hid/hid-sony.c)
- [External kernel modules / versioning](https://docs.kernel.org/kbuild/modules.html)
- [Linux hidraw](https://docs.kernel.org/hid/hidraw.html)
- [Android 14 EventHub](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-14.0.0_r1/services/inputflinger/reader/EventHub.cpp)
- [vmlinux-to-elf](https://github.com/marin-m/vmlinux-to-elf)
- [Magisk module guide](https://topjohnwu.github.io/Magisk/guides.html)
- [KernelSU module guide](https://kernelsu.org/guide/module.html) / [differences](https://kernelsu.org/guide/difference-with-magisk.html)
