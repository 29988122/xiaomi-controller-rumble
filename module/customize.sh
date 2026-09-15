# SPDX-License-Identifier: GPL-2.0-or-later
# Sourced by the Magisk / KernelSU-family installer; no driver is loaded here.
[ "$BOOTMODE" = true ] || abort 'Install from a running root-manager app, not recovery.'
[ "$ARCH" = arm64 ] || abort 'This profile requires ARM64.'
. "$MODPATH/profile.sh"
[ "$(uname -r)" = "$G8FF_KERNEL" ] || abort 'Unsupported kernel: this ZIP is firmware-specific.'
[ "$(getprop ro.build.fingerprint)" = "$G8FF_FINGERPRINT" ] || abort 'Unsupported ROM fingerprint.'
[ "$(sha256sum "$MODPATH/bin/sony_g8ff.ko" | cut -d ' ' -f 1)" = "$G8FF_SHA256" ] || abort 'Driver checksum mismatch.'
. "$MODPATH/lib/target.sh"
pick_target || abort 'Connect exactly ONE supported DS4 Bluetooth controller and wait for initialization, then retry.'
# Validated hex address and numeric interval only; never execute HID metadata.
cat "$MODPATH/profile.sh" > "$MODPATH/config.sh"
printf "G8FF_UNIQ='%s'\nG8FF_POLL='%s'\n" "$G8FF_SELECTED_UNIQ" "$G8FF_SELECTED_POLL" >> "$MODPATH/config.sh"
set_perm_recursive "$MODPATH" 0 0 0700 0600
set_perm "$MODPATH/bin/g8ffctl" 0 0 0700
set_perm "$MODPATH/bin/ff_test" 0 0 0700
touch "$MODPATH/disable" "$MODPATH/skip_mount"
ui_print 'One controller selected locally; no device identifier is uploaded.'
ui_print 'Installed DISABLED. Reboot to finish installation; review compatibility and recovery before enabling.'
