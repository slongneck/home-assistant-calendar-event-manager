# Calendar Event Manager

UID-aware calendar management for Home Assistant calendars, including Google Calendar.

## Installation

1. Copy `custom_components/calendar_event_manager` into the Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.
3. Add **Calendar Event Manager** from **Settings -> Devices & services -> Add Integration**.
4. Use the automatically registered **Calendar Event Manager** sidebar panel.

The integration uses only built-in Home Assistant components: `calendar`,
`frontend`, `http`, and `panel_custom`. It has no external Python dependencies
and does not require HACS after installation.

A calendar provider, such as Google Calendar, must be configured separately.
Google Calendar OAuth credentials are owned by the built-in Google integration;
this integration does not request or store them.

## Services

- `calendar_event_manager.preview` returns matching events with UID and recurrence information.
- `calendar_event_manager.delete` previews by default and deletes one event after exact confirmation.
- `calendar_event_manager.delete_matching` previews by default and requires an exact count confirmation.
- `calendar_event_manager.replace` previews by default and uses delete-then-create replacement.

The service responses include a `mutated` flag. No mutation occurs unless
`dry_run: false` and the required confirmation string match exactly.

## Optional Lovelace Card

The sidebar panel requires no Lovelace resource. The optional card is available
at `/calendar_event_manager/calendar-event-manager.js`.

For YAML-mode Lovelace, add this resource manually:

```yaml
lovelace:
  resources:
    - url: /calendar_event_manager/calendar-event-manager.js
      type: module
```

Then add:

```yaml
type: custom:calendar-event-manager
title: Calendar Event Manager
```

The card discovers accessible calendars at runtime and should not hard-code
Google account or personal calendar identifiers.
