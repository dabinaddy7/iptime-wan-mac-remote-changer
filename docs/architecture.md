# Architecture

## Overview

The system consists of four major components:

```text
Android / Termux
        │
        │ HTTP over WireGuard
        ▼
ipTIME Router
        │
        │ WAN MAC configuration
        ▼
ISP
        │
        │ New public IP
        ▼
DDNS
        │
        ▼
WireGuard reconnection
```

## Components

### Client

* Samsung Galaxy S25 Ultra
* Android
* Termux
* Python
* requests

The Python script runs entirely on the Android device.

### Router

* ipTIME A8004T-XR
* Firmware 14.27.6

The router exposes its management functionality through the internal `service.cgi` interface.

### VPN

WireGuard provides remote access to the router's LAN.

The phone receives a VPN address in the private WireGuard network.

Example:

```text
Router: 10.234.177.1
Phone : 10.234.177.2
```

### DDNS

The WireGuard client uses the router's DDNS hostname instead of a fixed public IP.

This is important because changing the WAN MAC can result in a different public IP address.

---

## Request Flow

```text
1. Start Python script
        ↓
2. Login
        ↓
3. Verify authentication
        ↓
4. Query WAN configuration
        ↓
5. Generate random MAC
        ↓
6. Copy existing WAN configuration
        ↓
7. Replace MAC field
        ↓
8. Send WAN configuration
        ↓
9. WAN reconnects
        ↓
10. Public IP may change
        ↓
11. WireGuard tunnel drops
        ↓
12. WireGuard OFF → ON
        ↓
13. DDNS resolves current public IP
        ↓
14. Remote access restored
```

---

## Why the existing WAN configuration is copied

The script does not construct the entire WAN configuration from scratch.

Instead:

```python
wan_config = copy.deepcopy(current)
wan_config["mac"] = new_mac
```

Only the MAC address is modified.

This reduces the risk of unintentionally changing unrelated WAN configuration values.

---

## MAC Address Generation

The generated MAC uses a locally administered unicast address.

```python
mac[0] = (mac[0] & 0xFC) | 0x02
```

The two least significant bits of the first octet are therefore:

```text
bit 1 = 1 → Locally Administered
bit 0 = 0 → Unicast
```

---

## Network Design

The WireGuard configuration can use split tunneling.

Example:

```text
10.234.177.0/24
192.168.0.0/24
```

Only the WireGuard network and router LAN are routed through the VPN.

Normal mobile internet traffic continues through the phone's mobile network.

This is useful because the WAN MAC change temporarily interrupts the VPN connection, while the phone itself remains connected to the mobile network.

---

## Important Design Decision

The project initially considered waiting for the router to reconnect and performing additional operations automatically.

However, WAN MAC changes can cause the current WireGuard connection to disappear before the remote client can communicate with the router again.

Therefore the final Termux workflow intentionally stops after requesting the MAC change.

The user then reconnects WireGuard:

```text
OFF → ON
```

The DDNS hostname allows the same WireGuard configuration to be reused after the public IP changes.

