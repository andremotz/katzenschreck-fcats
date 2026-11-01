# 0001. MQTT as the only interface to home automation

- Status: Accepted
- Date: 2024-12-30
- Commits: d272120, 166a174, 92c5c39, 9a47d11, 34df741, 7531af5, 1e223b0

## Context
The detector has to trigger a sprinkler. The sprinkler and all other automation live in Home Assistant, which already runs an MQTT broker.

## Decision
The detector only publishes MQTT messages. It does not control any actuator itself.

- One topic per class: `{mqtt_topic}/Cat`, `{mqtt_topic}/Person` (166a174, 1e223b0).
- JSON payload with time, class and confidence. QoS 0, because a late alert is worthless and should not be redelivered.
- Heartbeat on `{mqtt_topic}/ping` every 30 s with a timestamp (92c5c39, 9a47d11), so Home Assistant can tell when the detector is down.
- One persistent connection with auto-reconnect and a unique client id (34df741, 7531af5). Before that, a new connection was opened per message.

## Consequences
- What happens after a detection (sprinkler, how long, time windows) is decided entirely in Home Assistant and can be changed without touching the detector.
- End-to-end latency is split across two systems. Measured over 27 sprinkler runs (20.10.–01.11.2026): detection to Home Assistant trigger under about 1 s (estimated from image file names with one-second resolution), trigger to first sprinkler switched on median 0.2 s (max 1.4 s). The order and timing of the sprinklers is decided by the Home Assistant script (30.10.2026: sequence 1-2-3 at about 4 s each, so sprinkler 3 started about 9 s after the trigger).
- With QoS 0 a message lost during a broker restart is not repeated.
