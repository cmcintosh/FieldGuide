# Hardware testing

Initial targets are an ARM64 Android phone with 8 GB RAM, a Pi 5 with 8 GB RAM and cooling, and a laptop with 16 GB RAM. These are development targets, not measured requirements or compatibility guarantees.

Record device/OS, exact model hash and runtime commit, cold/warm load, first-token latency, complete answer time, peak RAM, thermal throttling and battery consumption. Test query cancellation, foreground/background behavior and recovery after the OS kills the process.

For maps, test offline cold start, bounds, missing tiles, attribution, correct TMS/XYZ rows, waypoint positioning and location behavior. For peers, test both independent devices, the actual hotspot/direct link, isolation rules, invalid/expired/revoked codes, interruption and repeat imports.

For audio, first measure both carriers at the receiver. Test audible and ultrasonic profiles separately, with varied orientation/distance/noise, and confirm received text against the sent text. Report frame success rate, error/rejection rate and transfer time. A successful decode of an unchanged generated WAV is not a hardware transmission test.

Airplane-mode testing must include a device restart. Enable only the specific radio needed for the local-link test; no cellular or upstream internet connection should be necessary. Real-model, Android, Pi and physical audio tests have not yet been performed in this environment.
