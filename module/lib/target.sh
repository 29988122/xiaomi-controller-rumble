# SPDX-License-Identifier: GPL-2.0-or-later
pick_target() {
    G8FF_COUNT=0
    for G8FF_CANDIDATE in /sys/bus/hid/devices/*; do
        [ -r "$G8FF_CANDIDATE/uevent" ] || continue
        grep -qx 'HID_ID=0005:0000054C:000005C4' "$G8FF_CANDIDATE/uevent" 2>/dev/null || continue
        G8FF_COUNT=$((G8FF_COUNT + 1))
        [ "$G8FF_COUNT" -eq 1 ] || return 1
        G8FF_BOUND=$(basename "$(readlink "$G8FF_CANDIDATE/driver")")
        case "$G8FF_BOUND" in sony|sony_g8ff) ;; *) return 1;; esac
        G8FF_SELECTED_UNIQ=$(sed -n 's/^HID_UNIQ=//p' "$G8FF_CANDIDATE/uevent") || return 1
        printf '%s\n' "$G8FF_SELECTED_UNIQ" | grep -Eq '^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$' || return 1
        G8FF_SELECTED_POLL=$(cat "$G8FF_CANDIDATE/bt_poll_interval" 2>/dev/null) || return 1
        case "$G8FF_SELECTED_POLL" in ''|*[!0-9]*) return 1;; esac
        [ "$G8FF_SELECTED_POLL" -ge 1 ] && [ "$G8FF_SELECTED_POLL" -le 62 ] || return 1
    done
    [ "$G8FF_COUNT" -eq 1 ]
}
