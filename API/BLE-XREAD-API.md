# RoastLink BLE Sensor API

## XREAD v1

`XREAD` is the versioned BLE sensor response for RoastLink integrations that need the complete set of available temperature, ambient, and humidity readings.

It is available on BLE-capable production firmware in the TWO and CORE families. ONE devices do not expose this BLE service.

## Transport

RoastLink uses a Nordic UART-style BLE service.

| Purpose | UUID |
| --- | --- |
| Service | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` |
| RX write | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` |
| TX notification | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` |

Write ASCII commands to RX. Subscribe to TX notifications before sending a command.

## Command

```text
XREAD
```

## Response

The device sends one semicolon-separated TX notification.

```text
XREAD;1;U=C;BT=205.4;BTOK=1;ET=218.7;ETOK=1;TH1=190.2;TH1OK=1;TH2=165.8;TH2OK=1;AT=22.3;ATOK=1;AH=42.0;AHOK=1\r\n
```

`XREAD;1` identifies the extension and response format version. Field order is fixed for version 1.

| Field | Meaning |
| --- | --- |
| `U` | Unit for every temperature value: `C` or `F`. Humidity is always percent relative humidity. |
| `BT` / `BTOK` | Bean thermocouple socket temperature and validity. |
| `ET` / `ETOK` | Environment thermocouple socket temperature and validity. |
| `TH1` / `TH1OK` | Thermistor channel 1 temperature and validity. |
| `TH2` / `TH2OK` | Thermistor channel 2 temperature and validity. |
| `AT` / `ATOK` | SHT31 ambient temperature and validity. |
| `AH` / `AHOK` | SHT31 relative humidity and validity. |

For an unavailable, disconnected, or invalid sensor, its value is `nan` and the matching `OK` field is `0`.

```text
XREAD;1;U=F;BT=401.7;BTOK=1;ET=425.2;ETOK=1;TH1=nan;TH1OK=0;TH2=176.4;TH2OK=1;AT=nan;ATOK=0;AH=nan;AHOK=0\r\n
```

`BT` and `ET` are reported independently. A failed thermocouple socket is never substituted with the value from the other socket.

## Sensor Mapping

| Device family | `TH1` | `TH2` |
| --- | --- | --- |
| TWO | Optional NTC or ADS1115 channel | Unavailable |
| TWO+ / TWO+ V2 | Board NTC | Unavailable |
| TWO+ V3 | BT socket thermistor | ET socket thermistor |
| CORE | Optional NTC or ADS1115 channel | Unavailable |
| CORE V2 / CORE V3 | Thermistor GPIO1 | Thermistor GPIO2 |

`AT` and `AH` are available whenever the optional SHT31 sensor is detected.

## Client Requirements

1. Subscribe to TX notifications before writing `XREAD`.
2. Send `XREAD` whenever a fresh sample is required.
3. Check each `OK` flag before consuming its paired value.
4. Read `U` from every response; do not assume a temperature unit.
5. Treat `nan` as unavailable data, not as a numeric value.

## Compatibility

`XREAD` is an opt-in extension. It does not alter existing BLE command behavior or legacy telemetry responses.
