# RoastLink WebSocket API

Applies to production **ONE**, **TWO**, and **CORE** firmware. COREDEV is not covered.

Endpoint: `ws://<device-ip>:81/`  
Transport: UTF-8 text frames. Commands and data use JSON.

All temperatures are **degrees Fahrenheit**. Humidity is percent RH.

## Read temperatures

Send:

```json
{"id":1,"command":"getData"}
```

Receive:

```json
{"id":1,"data":{"BT":401.7,"ET":425.2,"ET2":176.4,"ET3":165.8,"AT":77.0,"AH":42.0}}
```

| Field | Meaning |
| --- | --- |
| `BT` | Bean thermocouple temperature. |
| `ET` | Environment thermocouple temperature. |
| `ET2` | First optional extra temperature. |
| `ET3` | Second optional extra temperature. |
| `AT` | SHT31 ambient temperature. |
| `AH` | SHT31 relative humidity. |

`BT` and `ET` are always returned. Other fields are omitted when unavailable. `id` is optional and echoed in the reply (`0` when omitted).

| Family | Extra temperature fields |
| --- | --- |
| ONE / ONE V2 | `ET2` is the optional NTC reading. |
| TWO | `ET2` is the optional NTC/ADS1115 reading. |
| TWO+ / TWO+ V2 / TWO+ V3 | `ET2` is the switching-thermistor reading. |
| CORE | `ET2` is the optional NTC/ADS1115 reading. |
| CORE V2 / CORE V3 | `ET2` and `ET3` are thermistor channels 1 and 2. |

`getData` is compatibility-oriented: if a BT or ET probe is invalid, firmware can temporarily mirror the other probe or retain its last valid value. Treat it as a current, filtered readout, not independent sensor validity.

## Control

The command form is:

```json
{"command":"fan_pct","data":65}
```

| Commands | Data | Available on |
| --- | --- | --- |
| `fan` | level `0`-`10` | CORE family |
| `fan_pct` | percent `0`-`100` | CORE family |
| `fan_nudge` | signed percent change | CORE family |
| `heater` | level `0`-`10` | CORE family |
| `heater_pct` | percent `0`-`100` | CORE family |
| `heater_nudge` | signed percent change | CORE family |
| `cooldown` | none | CORE family: heater off, fan full |
| `off` | none | CORE family: heater and fan off |
| `pid_on`, `pid_off` | none | CORE family |
| `pid_sv` | target in degrees C | CORE family |
| `pid_tunings` | `{"kp":...,"ki":...,"kd":...,"pm":"M"}` | CORE family |
| `mirror_enabled` | `0` or `1` | All production families |

Values may be sent directly as `data` or as `{"data":{"value":...}}`.

## Roast log events

```json
{"command":"start"}
{"command":"fcstart"}
{"command":"drop"}
```

Supported commands: `start`, `stop`, `charge`, `dryend`, `fcstart`, `fcend`, `scstart`, `scend`, and `drop`.

They update the device log after the client sends `hello_ui`, or when **Artisan Event Sync** is enabled in device settings.

## Optional UI stream

Send this plain-text frame once after connecting:

```text
hello_ui
```

The device then sends telemetry and state frames such as:

```json
{"et":425.2,"bt":401.7,"et2":176.4,"et3":165.8,"at":77.0,"ah":42,"t":1234}
{"fan":5,"heater":4}
{"type":"start","elapsed":38}
{"type":"ev","t":42,"label":"First Crack Start"}
```

Telemetry uses lowercase temperature names. Optional readings are omitted when unavailable. `t` and event times are device uptime seconds. The control frame is sent after the handshake and whenever a control changes.

TWO+ V2, TWO+ V3, and CORE V3 additionally send thermocouple health frames:

```json
{"type":"sensorHealth","btValid":true,"etValid":true,"btState":"ok","etState":"ok","btFault":0,"etFault":0,"btLastValidAgeMs":0,"etLastValidAgeMs":0,"btRecoveries":0,"etRecoveries":0}
```

States are `ok`, `fault`, or `recovering`. Use `btValid` and `etValid` before treating a thermocouple reading as live. This frame is not available on the other production variants.

Clients that only use `getData` should not send `hello_ui`; they will receive only direct command responses.

## Keepalive

```text
ping
```

Response:

```text
pong
```
