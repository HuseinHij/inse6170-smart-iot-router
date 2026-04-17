# Architecture

## Logical flow

Internet/Cloud <-> Linux Router/Hotspot <-> IoT devices

The Linux host is the control point. It provides hotspot access, routes traffic, applies firewall and traffic-control rules, captures traffic, detects excessive behavior, and stores operational data in SQLite.

## Modules

- Device discovery and inventory
- OUI-based device vendor identification
- Packet capture and PCAP storage
- Firewall whitelist management
- Rate/anomaly monitoring
- Temporary device throttling
- SQLite-backed logs, state, and alerts
- Local web dashboard
