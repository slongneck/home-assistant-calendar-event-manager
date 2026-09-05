# Calendar Event Manager

UID-aware calendar management for Home Assistant calendars, including Google Calendar.

## Installation

1. Copy `custom_components/calendar_event_manager` into the Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.
3. Add **Calendar Event Manager** from **Settings -> Devices & services -> Add Integration**.
4. Use the automatically registered **Calendar Event Manager** sidebar panel.

The integration has no external Python dependencies. A calendar provider, such as
Google Calendar, must be configured separately.

## Services

- `calendar_event_manager.preview` returns matching events with UID and recurrence information.
- `calendar_event_manager.delete` previews by default and deletes one event after exact confirmation.
- `calendar_event_manager.delete_matching` previews by default and requires an exact count confirmation.
- `calendar_event_manager.replace` previews by default and uses delete-then-create replacement.
- `calendar_event_manager.adopt` previews by default and updates a writable Google recurring series in place.

The service responses include a `mutated` flag. No mutation occurs unless
`dry_run: false` and the required confirmation string match exactly.

Replacing an event creates a new UID. Adopting a recurring Google series
preserves its recurrence and UID and requires a writable base calendar entity,
not a filtered search entity.

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
