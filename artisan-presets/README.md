# RoastLink presets for Artisan

Run `./install-into-artisan.sh`. It creates a separate user-owned copy at
`~/Applications/Artisan.app`, installs the presets there, and ad-hoc signs that copy.
The presets appear under `Config > Machine > RoastLink`.

All presets poll `ws://roastlink.local:81/` using the RoastLink `getData` command.
`CORE.aset` additionally exposes the Air and Power sliders for the firmware's
`fan_pct` and `heater_pct` commands.

The original app in `/Applications` is not changed. Re-run the installer after updating
Artisan to create a new customized copy.
