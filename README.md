# Yale Linus L2 / L2 Lite

Home Assistant custom integration providing native unlatch/open and diagnostic helpers for the Yale Linus L2 Lite.

## Requirements

Configure the built-in **Yale Access Bluetooth** integration first. This integration depends on `yalexs_ble` and reuses its existing BLE connection and credentials. A Bluetooth adapter or ESPHome Bluetooth proxy is required.

## Install with HACS

Add this GitHub repository as a custom **Integration** repository in HACS, install, restart Home Assistant, then add the integration in Settings → Devices & services.

## Migrating an existing manual installation

Back up `custom_components/linus_l2_unlatch` and your Home Assistant configuration. Install the same integration domain through HACS without creating a duplicate config entry. Restart and confirm your existing entities remain present.

## Limitations

Battery percentage and voltage are not verified for L2 Lite. The upstream Yale Access Bluetooth integration must remain configured and working.

## Status

v0.6.0 HACS packaging of the existing v0.5.0 integration; no BLE protocol changes. Hardware compatibility outside the original tested lock is not established.