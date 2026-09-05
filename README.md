# Home Assistant Calendar Event Manager

Preview, search, create, replace, and safely delete Home Assistant calendar
events, including Google Calendar events.

The integration is provider-neutral. It works with calendar entities that
support the required Home Assistant calendar operations. Google Calendar is
the primary tested use case, but no Google API credentials are stored by this
project. Configure the Google Calendar integration separately.

## Features

- UID- and recurrence-aware event preview
- Preview-first deletion and replacement
- Exact confirmation required for mutations
- Delete-then-create replacement fallback
- Automatically registered admin sidebar panel
- Optional Lovelace card with runtime calendar discovery
- No external Python dependencies

## Install

1. Install through HACS as a custom repository, or copy
   `custom_components/calendar_event_manager` into `config/custom_components`.
2. Restart Home Assistant.
3. Add **Calendar Event Manager** from **Settings -> Devices & services -> Add Integration**.
4. Open the automatically registered **Calendar Event Manager** sidebar panel.

## Services

- `calendar_event_manager.preview`
- `calendar_event_manager.delete`
- `calendar_event_manager.delete_matching`
- `calendar_event_manager.replace`

Mutating services default to preview mode. Applying a mutation requires
`dry_run: false` and the exact confirmation returned by the preview response.
Replacing an event creates a new UID.

## Optional Lovelace Card

The sidebar panel requires no Lovelace resource. The optional card is provided
at `/calendar_event_manager/calendar-event-manager.js` after the integration is configured.

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

The card discovers accessible calendars at runtime and does not require
personal calendar IDs in its configuration.

## Safety

Use `preview` before any destructive operation. For automatic reconciliation,
mark generated events with a project-owned description tag and restrict cleanup
to those marked events. Do not use broad, unbounded deletion for ordinary
calendar maintenance.
