# SPDX-License-Identifier: GPL-2.0-or-later
# Return 2 only for a single valid controller whose driver is still initializing.
pick_target() {
    G8FF_ERROR=''
    G8FF_COUNT=0
    G8FF_SELECTED_UNIQ=''
    G8FF_SELECTED_POLL=''
    for G8FF_CANDIDATE in /sys/bus/hid/devices/*; do
        [ -r "$G8FF_CANDIDATE/uevent" ] || continue
        grep -qx 'HID_ID=0005:0000054C:000005C4' "$G8FF_CANDIDATE/uevent" 2>/dev/null || continue
        G8FF_COUNT=$((G8FF_COUNT + 1))
        G8FF_SELECTED_PATH=$G8FF_CANDIDATE
    done
    case "$G8FF_COUNT" in
        0) G8FF_ERROR='[controller:none] No supported DS4 Bluetooth controller found. Connect it in DS4 mode, then retry.'; return 1;;
        1) ;;
        *) G8FF_ERROR='[controller:multiple] More than one supported DS4 controller found. Disconnect the others, then retry.'; return 1;;
    esac
    G8FF_SELECTED_UNIQ=$(sed -n 's/^HID_UNIQ=//p' "$G8FF_SELECTED_PATH/uevent") || return 1
    if [ "${#G8FF_SELECTED_UNIQ}" -ne 17 ] || ! printf '%s\n' "$G8FF_SELECTED_UNIQ" | grep -Eq '^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'; then
        G8FF_ERROR='[controller:identity] Controller identity is missing or invalid; installation stopped.'
        return 1
    fi
    if [ -n "${G8FF_PINNED_UNIQ:-}" ] && [ "$G8FF_SELECTED_UNIQ" != "$G8FF_PINNED_UNIQ" ]; then
        G8FF_ERROR='[controller:changed] The connected controller changed during installation. Retry with only the intended controller.'
        return 1
    fi
    G8FF_BOUND=$(readlink "$G8FF_SELECTED_PATH/driver" 2>/dev/null)
    G8FF_BOUND=${G8FF_BOUND##*/}
    case "$G8FF_BOUND" in
        sony|sony_g8ff) ;;
        '') G8FF_ERROR='[controller:unbound] One DS4 controller found, but its Sony driver did not initialize. Power the controller fully off/on and reconnect in DS4 mode, then retry. If this repeats, check the kernel log for Sony calibration errors.'; return 2;;
        *) G8FF_ERROR='[controller:driver] The controller is using an unsupported driver; installation stopped.'; return 1;;
    esac
    if ! G8FF_SELECTED_POLL=$(cat "$G8FF_SELECTED_PATH/bt_poll_interval" 2>/dev/null); then
        G8FF_ERROR='[controller:initializing] One DS4 controller found, but its Sony driver is not ready. Power the controller off/on and reconnect, then retry.'
        return 2
    fi
    case "$G8FF_SELECTED_POLL" in
        ''|*[!0-9]*) G8FF_ERROR='[controller:poll] Invalid Bluetooth polling interval; installation stopped.'; return 1;;
    esac
    if [ "$G8FF_SELECTED_POLL" -lt 1 ] || [ "$G8FF_SELECTED_POLL" -gt 62 ]; then
        G8FF_ERROR='[controller:poll] Bluetooth polling interval is outside 1..62; installation stopped.'
        return 1
    fi
    return 0
}

wait_for_target() {
    G8FF_PINNED_UNIQ=''
    G8FF_ATTEMPT=0
    while :; do
        if pick_target; then return 0; else G8FF_RESULT=$?; fi
        [ "$G8FF_RESULT" -eq 2 ] || return 1
        [ "$G8FF_ATTEMPT" -lt 20 ] || return 1
        if [ "$G8FF_ATTEMPT" -eq 0 ]; then
            G8FF_PINNED_UNIQ=$G8FF_SELECTED_UNIQ
            ui_print 'One DS4 controller detected; waiting up to 20 seconds for Sony driver initialization...'
        fi
        G8FF_ATTEMPT=$((G8FF_ATTEMPT + 1))
        sleep 1
    done
}
