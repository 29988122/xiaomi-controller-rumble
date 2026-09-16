# SPDX-License-Identifier: GPL-2.0-or-later
G8FF_LOCALE=$(getprop persist.sys.locale)
[ -n "$G8FF_LOCALE" ] || G8FF_LOCALE=$(getprop ro.product.locale)
msg() { case "$G8FF_LOCALE" in zh*) printf '%s\n' "$1";; *) printf '%s\n' "$2";; esac; }
valid_uniq() {
    [ "${#1}" -eq 17 ] && printf '%s\n' "$1" | grep -Eq '^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
}
valid_poll() {
    case "$1" in ''|*[!0-9]*) return 1;; esac
    [ "${#1}" -le 2 ] && [ "$1" -ge 1 ] && [ "$1" -le 62 ]
}
# Read only known literal fields. Never execute an old installation's config.
read_config() {
    [ -f "$1" ] && [ ! -L "$1" ] || return 1
    G8FF_UNIQ=$(sed -n "s/^G8FF_UNIQ='\([^']*\)'$/\1/p" "$1")
    G8FF_POLL=$(sed -n "s/^G8FF_POLL='\([^']*\)'$/\1/p" "$1")
    valid_uniq "$G8FF_UNIQ" && valid_poll "$G8FF_POLL"
}
write_config() {
    valid_uniq "$G8FF_SELECTED_UNIQ" && valid_poll "$G8FF_SELECTED_POLL" || return 1
    (umask 077; printf "G8FF_UNIQ='%s'\nG8FF_POLL='%s'\n" "$G8FF_SELECTED_UNIQ" "$G8FF_SELECTED_POLL" > "$1.tmp.$$" && mv -f "$1.tmp.$$" "$1")
}
compatible() {
    [ "$(uname -r)" = "$G8FF_KERNEL" ] &&
    [ "$(getprop ro.build.fingerprint)" = "$G8FF_FINGERPRINT" ] &&
    [ "$(sha256sum "$G8FF_DIR/bin/sony_g8ff.ko" | cut -d ' ' -f 1)" = "$G8FF_SHA256" ] &&
    [ "$(sha256sum "$G8FF_DIR/bin/ff_test" | cut -d ' ' -f 1)" = "$G8FF_TEST_SHA256" ]
}
controller_help() {
    case "$G8FF_ERROR" in
        *controller:none*) msg '請以 DS4 模式連接手把，再按「動作」。' 'Connect the controller in DS4 mode, then press Action.';;
        *controller:multiple*) msg '找到多支符合條件的手把。只保留想設定的那支，再按「動作」。' 'Multiple supported controllers found. Leave only the intended one connected, then press Action.';;
        *controller:changed*) msg '等待時手把已變更。請只連目標手把，再按「動作」。' 'The controller changed while waiting. Connect only the intended controller, then press Action.';;
        *controller:unbound*|*controller:initializing*) msg '手把已連線，但尚未準備好。請將手把關機重開、重新連線，再按「動作」。' 'The controller is connected but not ready. Power it off/on, reconnect, then press Action.';;
        *) msg '無法確認手把狀態，未變更設定。請重新連接支援的 DS4 手把。' 'Controller state could not be verified; settings were not changed. Reconnect a supported DS4 controller.';;
    esac
}
