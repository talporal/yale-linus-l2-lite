"""Constants for Linus L2 Native Open."""

from datetime import timedelta

DOMAIN = "linus_l2_unlatch"
CONF_YALEXSBLE_ENTRY_ID = "yalexs_ble_entry_id"

UNLATCH_OPERATION_BYTE = 0x0A
L2_LOCK_STATUS_SELECTOR = 0x02
L2_BATTERY_STATUS_SELECTOR = 0x03

# Hardware-validated on the user's Linus L2 Lite:
L2_STATUS_UNLOCKED = 0x02
L2_STATUS_LOCKED = 0x04

# Poll often enough to notice a physical-button change without being excessive.
LOCK_STATUS_REFRESH_INTERVAL = timedelta(seconds=10)
BATTERY_REFRESH_INTERVAL = timedelta(minutes=15)
