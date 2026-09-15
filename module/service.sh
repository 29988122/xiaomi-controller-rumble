#!/system/bin/sh
MODDIR=${0%/*}
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 2; done
[ -e "$MODDIR/disable" ] && exit 0
exec sh "$MODDIR/bin/g8ffctl" watch
