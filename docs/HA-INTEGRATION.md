# Home Assistant Integration

The RejseplanAPI custom component turns your self-hosted departure backend into Home Assistant entities. Each configured stop/line combo becomes a device with sensors you can use in automations, dashboards, and TTS announcements.

## Prerequisites

- Home Assistant 2024.1 or later
- A running RejseplanAPI backend reachable from your Home Assistant instance
- The backend URL (e.g. `http://192.168.1.50:8000` or `http://192.168.1.50` if behind nginx)

## Installation

### Manual (recommended)

```bash
# From your Home Assistant config directory (wherever configuration.yaml lives)
cp -r /path/to/rejseplanapi/ha-integration/custom_components/rejseplan \
      /config/custom_components/rejseplan
```

Restart Home Assistant. The integration will appear in the Integrations list.

### Via HACS

1. Open HACS in your Home Assistant sidebar.
2. Go to **Integrations**.
3. Click the three-dot menu (top right) → **Custom repositories**.
4. Add repository URL: `https://github.com/jonaslarsen0/dograllyblazorserver`
5. Set category to **Integration**.
6. Click **Add**.
7. Search "Rejseplanen" in HACS Integrations and click **Download**.
8. Restart Home Assistant.

## Adding an Integration Entry

1. Go to **Settings → Devices & Services**.
2. Click **Add Integration** (bottom right).
3. Search for **RejseplanAPI** and select it.

You will walk through three steps:

### Step 1 — API URL

Enter the base URL of your RejseplanAPI backend. Do **not** include a trailing slash or `/api`.

| Scenario | URL to enter |
|---|---|
| Backend on the same machine as HA | `http://localhost:8000` |
| Backend in Docker on the same machine | `http://localhost:8000` (or `http://172.17.0.1:8000`) |
| Backend on a Proxmox VM at 192.168.1.50 | `http://192.168.1.50` (via nginx) |
| Backend direct (no nginx) on 192.168.1.50 | `http://192.168.1.50:8000` |

The integration validates the URL by hitting `/api/departures/0` — any HTTP response counts as reachable. If you see a "Cannot connect" error, verify the backend is running (`docker compose ps`) and reachable from the HA host.

### Step 2 — Search for a stop

Type part of a stop name and press **Submit**. The integration calls your backend's `GET /api/stops/search` endpoint. If no results appear, confirm the backend is returning data: `curl "http://<your-backend>/api/stops/search?q=Odense"`.

### Step 3 — Configure route

| Field | Description | Example |
|---|---|---|
| **Stop** | Select from the dropdown of search results | Odense St. |
| **Line filter** | (Optional) Only track departures matching this string. Case-insensitive, partial match. Leave blank to track all lines. | `IC` |
| **Walk time** | Minutes you need to reach the stop. Drives the `go_now` binary sensor. Use the slider (1–30 min). | `7` |

Click **Submit**. The device and its five entities are created immediately.

Repeat for each stop/line combination you want to track. A busy commuter might have: "Odense IC", "Odense RE", "Nyborg IC".

### Options (post-setup)

To change the walk time after setup: go to the integration entry → **Configure** → adjust the walk time slider.

---

## Entities

Each configured entry creates one **device** with five entities. Names use the pattern `<stop>_<line>` (slugified).

For a setup named "Odense St. IC":

| Entity ID | Type | Device class | Unit |
|---|---|---|---|
| `sensor.rejseplan_odense_st_ic_next_departure` | Sensor | `timestamp` | — |
| `sensor.rejseplan_odense_st_ic_delay_minutes` | Sensor | — | minutes |
| `sensor.rejseplan_odense_st_ic_minutes_until` | Sensor | — | minutes |
| `binary_sensor.rejseplan_odense_st_ic_go_now` | Binary sensor | — | on/off |
| `binary_sensor.rejseplan_odense_st_ic_cancelled` | Binary sensor | `problem` | on/off |

### `next_departure` sensor

State: ISO-8601 datetime of the expected departure (uses `expected_time` if available, `planned_time` otherwise).

Extra state attributes:
- `line` — e.g. `"IC"`
- `direction` — e.g. `"København H"`
- `delay_minutes` — integer
- `track` — platform number or null
- `vehicle_type` — e.g. `"IC"`

### `delay_minutes` sensor

State: integer minutes of current delay. 0 = on time.

### `minutes_until` sensor

State: float minutes until the next departure. Counts down in real time (updated every 30 seconds). Null when no upcoming departure is found.

### `go_now` binary sensor

State: `on` when the next departure is within `walk_time` minutes and is not cancelled.

Extra state attributes:
- `walk_time_minutes` — the configured walk time
- `departure_time` — ISO datetime
- `line`, `direction`

### `cancelled` binary sensor

State: `on` when the next upcoming departure is flagged as cancelled by Rejseplanen. Device class `problem` means it shows as a warning in dashboards.

---

## Lovelace Cards

### Basic entities card

```yaml
type: entities
title: Odense → København
entities:
  - entity: sensor.rejseplan_odense_st_ic_next_departure
    name: Næste IC
  - entity: sensor.rejseplan_odense_st_ic_delay_minutes
    name: Forsinkelse
  - entity: sensor.rejseplan_odense_st_ic_minutes_until
    name: Minutter til afgang
  - entity: binary_sensor.rejseplan_odense_st_ic_go_now
    name: Gå nu
  - entity: binary_sensor.rejseplan_odense_st_ic_cancelled
    name: Aflyst
```

### Glance card for a wall panel

```yaml
type: glance
title: Tog
entities:
  - entity: sensor.rejseplan_odense_st_ic_minutes_until
    name: IC om
  - entity: sensor.rejseplan_odense_st_ic_delay_minutes
    name: Forsinkelse
  - entity: binary_sensor.rejseplan_odense_st_ic_go_now
    name: Gå nu!
  - entity: binary_sensor.rejseplan_odense_st_ic_cancelled
    name: Aflyst
show_state: true
```

### Conditional card — only show when it is time to leave

```yaml
type: conditional
conditions:
  - entity: binary_sensor.rejseplan_odense_st_ic_go_now
    state: "on"
card:
  type: alert
  entity: binary_sensor.rejseplan_odense_st_ic_go_now
  title: Tid til at gå!
  content: >
    IC mod København kører om
    {{ states('sensor.rejseplan_odense_st_ic_minutes_until') | round(0) }} minutter.
    {% if states('sensor.rejseplan_odense_st_ic_delay_minutes') | int > 0 %}
    ({{ states('sensor.rejseplan_odense_st_ic_delay_minutes') }} min forsinket)
    {% endif %}
```

---

## Automation Examples

### TTS announcement when it is time to leave

```yaml
alias: "Tog: Gå nu annoncering"
description: >
  Announce over speakers when it is time to leave for the IC to Copenhagen.
trigger:
  - platform: state
    entity_id: binary_sensor.rejseplan_odense_st_ic_go_now
    to: "on"
condition:
  - condition: time
    after: "06:00:00"
    before: "09:00:00"
  - condition: state
    entity_id: binary_sensor.rejseplan_odense_st_ic_cancelled
    state: "off"
action:
  - service: tts.speak
    target:
      entity_id: tts.google_translate_en
    data:
      cache: false
      message: >
        IC til København kører om
        {{ states('sensor.rejseplan_odense_st_ic_minutes_until') | round(0) | int }}
        minutter.
        {% set delay = states('sensor.rejseplan_odense_st_ic_delay_minutes') | int %}
        {% if delay > 0 %}
        Toget er {{ delay }} minutter forsinket.
        {% endif %}
mode: single
```

### Push notification when a train is cancelled

```yaml
alias: "Tog: Aflysningsadvarsel"
trigger:
  - platform: state
    entity_id: binary_sensor.rejseplan_odense_st_ic_cancelled
    to: "on"
condition:
  - condition: time
    after: "05:30:00"
    before: "21:00:00"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "Tog aflyst"
      message: >
        Næste IC fra Odense mod
        {{ state_attr('sensor.rejseplan_odense_st_ic_next_departure', 'direction') }}
        er AFLYST.
      data:
        push:
          sound: default
mode: single
```

### Notification on large delays (60+ minutes)

```yaml
alias: "Tog: Stor forsinkelse"
trigger:
  - platform: numeric_state
    entity_id: sensor.rejseplan_odense_st_ic_delay_minutes
    above: 59
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "Stor forsinkelse"
      message: >
        IC fra Odense er
        {{ states('sensor.rejseplan_odense_st_ic_delay_minutes') }}
        minutter forsinket. Overvej kompensationskrav.
mode: single
```

### Turn on a smart light when it is time to go

```yaml
alias: "Tog: Lysadvarsel"
trigger:
  - platform: state
    entity_id: binary_sensor.rejseplan_odense_st_ic_go_now
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.gang_lampe
    data:
      color_name: orange
      brightness_pct: 100
  - wait_for_trigger:
      - platform: state
        entity_id: binary_sensor.rejseplan_odense_st_ic_go_now
        to: "off"
  - service: light.turn_off
    target:
      entity_id: light.gang_lampe
mode: restart
```

---

## Troubleshooting

**"Cannot connect" at step 1**

- Is the backend running? `docker compose ps`
- Can HA reach the host? `ping 192.168.1.50` from the HA terminal (Developer Tools → Shell)
- Is the firewall open on port 80 (or 8000)?

**No stops found at step 2**

- Is the backend returning results? `curl "http://<backend>/api/stops/search?q=Odense"`
- Check backend logs: `docker compose logs backend`

**Entities stuck as "unavailable"**

- Check that the backend is running and the `next_departure` endpoint returns data
- Look at the coordinator errors in HA logs: **Settings → System → Logs**, filter by `rejseplan`

**`go_now` never triggers**

- Verify `walk_time_minutes` in the `go_now` binary sensor's attributes. If it shows 5, the sensor turns on when `minutes_until <= 5`.
- `minutes_until` updates every 30 seconds. The sensor may lag by up to 30 seconds.
- The sensor is `off` when the departure is cancelled, even if the timing would otherwise match.
