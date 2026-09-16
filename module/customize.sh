# SPDX-License-Identifier: GPL-2.0-or-later
. "$MODPATH/lib/common.sh"
ui_print "$(msg '1/3 檢查手機' '1/3 Check phone')"
[ "$BOOTMODE" = true ] || abort "$(msg '請從手機的 root 管理器安裝。' 'Install from the root-manager app on the running phone.')"
[ "$ARCH" = arm64 ] || abort "$(msg '這個安裝包只支援 ARM64。' 'This package requires ARM64.')"
. "$MODPATH/profile.sh"
[ "$(uname -r)" = "$G8FF_KERNEL" ] || abort "$(msg '核心版本不符合，未安裝。需要：' 'Kernel mismatch; not installed. Required:') $G8FF_KERNEL"
[ "$(getprop ro.build.fingerprint)" = "$G8FF_FINGERPRINT" ] || abort "$(msg '系統版本不符合，未安裝。需要：' 'ROM mismatch; not installed. Required:') $G8FF_FINGERPRINT"
G8FF_DIR=$MODPATH
compatible || abort "$(msg '檔案校驗失敗，請重新下載安裝包。' 'File verification failed. Download the package again.')"
command -v flock >/dev/null && command -v setsid >/dev/null || abort "$(msg '管理器缺少執行工具，請更新 root 管理器。' 'Required runtime tools are missing. Update the root manager.')"
ui_print "$(msg '手機版本符合。' 'Phone version matches.')"
ui_print "$(msg '2/3 設定手把' '2/3 Set up controller')"
# Only the active installation is a migration source; no untrusted shell sourcing.
G8FF_OLD=/data/adb/modules/sony_g8ff_ruby
if read_config "$G8FF_OLD/config.sh"; then
    G8FF_SELECTED_UNIQ=$G8FF_UNIQ
    G8FF_SELECTED_POLL=$G8FF_POLL
    write_config "$MODPATH/config.sh" || abort 'Cannot save controller settings.'
    ui_print "$(msg '已保留原本的手把設定。' 'Existing controller settings retained.')"
elif [ -e "$G8FF_OLD/config.sh" ]; then
    ui_print "$(msg '舊設定無法確認。安裝後請按「動作」重新設定。' 'Old settings could not be verified. Press Action after reboot to set up the controller.')"
else
    . "$MODPATH/lib/target.sh"
    if pick_target; then
        write_config "$MODPATH/config.sh" || abort 'Cannot save controller settings.'
        ui_print "$(msg '已記住手把。' 'Controller saved.')"
    else
        ui_print "$(msg '手把尚未設定，仍可完成安裝。' 'Controller setup is pending; installation can continue.')"
        ui_print "$(controller_help)"
    fi
fi
# Record the installing boot; Action must not execute staged/new files early.
cat /proc/sys/kernel/random/boot_id > "$MODPATH/install.boot" || abort 'Cannot record installation boot.'
if [ -e "$G8FF_OLD/disable" ]; then
    touch "$MODPATH/disable" || abort 'Cannot preserve disabled state.'
fi
set_perm_recursive "$MODPATH" 0 0 0700 0600 || abort "$(msg '無法完成檔案權限設定，未完成安裝。' 'Cannot finish file permissions; installation incomplete.')"
set_perm "$MODPATH/bin/g8ffctl" 0 0 0700 || abort "$(msg '無法完成檔案權限設定，未完成安裝。' 'Cannot finish file permissions; installation incomplete.')"
set_perm "$MODPATH/bin/ff_test" 0 0 0700 || abort "$(msg '無法完成檔案權限設定，未完成安裝。' 'Cannot finish file permissions; installation incomplete.')"
set_perm "$MODPATH/action.sh" 0 0 0700 || abort "$(msg '無法完成檔案權限設定，未完成安裝。' 'Cannot finish file permissions; installation incomplete.')"
touch "$MODPATH/skip_mount" || abort "$(msg '無法完成檔案權限設定，未完成安裝。' 'Cannot finish file permissions; installation incomplete.')"
ui_print "$(msg '3/3 安裝完成，請重新開機一次。' '3/3 Installed. Reboot once.')"
if [ -e "$MODPATH/disable" ]; then
    ui_print "$(msg '已保留停用狀態。重開機後開啟模組開關，再按「動作」即可啟動。' 'Disabled state retained. After reboot, enable the module and press Action to start.')"
else
    ui_print "$(msg '重開機後可按「動作」完成設定或測試震動，不需再重開機。' 'After reboot, press Action to finish setup or test rumble. No second reboot is needed.')"
fi
