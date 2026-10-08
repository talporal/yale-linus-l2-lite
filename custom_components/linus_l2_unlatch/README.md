# Linus L2 Native Open v0.5.0

## Main change: L2 Lite physical-button state

Hardware captures from the target Linus L2 Lite established:

- selector 0x02, byte 8 = 0x02 -> UNLOCKED
- selector 0x02, byte 8 = 0x04 -> LOCKED

The custom lock now polls this status every 10 seconds and parses it directly.
This allows a physical lock/unlock action on the device to be reflected in the
custom Home Assistant entity even though released yalexs_ble reports Unknown.

The custom entity also refreshes directly after HA lock/unlock/open commands.

## Battery correction

v0.4.0 incorrectly assumed the Linus L2 Lite used the same battery millivolt
encoding observed on another Linus L2 variant.

The target L2 Lite returned:

    bb0200550300000026c50000000000000000

Interpreting bytes 8:10 as little-endian millivolts gives 50.470 V, which is not
credible for this lock. v0.5.0 therefore stops exposing that value.

Battery percentage and voltage remain Unknown until the L2 Lite-specific 0x03
payload encoding is verified. The raw response continues to be logged for
research.

## Upgrade

Replace:

    /config/custom_components/linus_l2_unlatch/

with this version and restart Home Assistant.
