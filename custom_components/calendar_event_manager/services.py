from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import calendar
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CONFIRMATION,
    CONF_DESCRIPTION,
    CONF_DRY_RUN,
    CONF_END,
    CONF_ENTITY_ID,
    CONF_LOCATION,
    CONF_MATCH,
    CONF_RECURRENCE_ID,
    CONF_RECURRENCE_RANGE,
    CONF_START,
    CONF_SUMMARY,
    CONF_UID,
    CONFIRM_DELETE,
    CONFIRM_DELETE_MATCHING,
    CONFIRM_REPLACE,
    DOMAIN,
    MATCH_CONTAINS,
    MATCH_EXACT,
    SERVICE_DELETE,
    SERVICE_DELETE_MATCHING,
    SERVICE_PREVIEW,
    SERVICE_REPLACE,
)

_LOGGER = logging.getLogger(__name__)

_ENTITY_SCHEMA = vol.All(cv.entity_id, cv.entity_domain("calendar"))
_DATE_VALUE = vol.Any(cv.datetime, cv.date)
_COMMON_FILTER_FIELDS = {
    vol.Required(CONF_ENTITY_ID): _ENTITY_SCHEMA,
    vol.Optional(CONF_START): _DATE_VALUE,
    vol.Optional(CONF_END): _DATE_VALUE,
    vol.Optional(CONF_SUMMARY, default=""): cv.string,
    vol.Optional(CONF_DESCRIPTION, default=""): cv.string,
    vol.Optional(CONF_MATCH, default=MATCH_EXACT): vol.In(
        [MATCH_EXACT, MATCH_CONTAINS]
    ),
}

SERVICE_PREVIEW_SCHEMA = vol.Schema(_COMMON_FILTER_FIELDS)
SERVICE_DELETE_MATCHING_SCHEMA = vol.Schema(
    {
        **_COMMON_FILTER_FIELDS,
        vol.Optional(CONF_DRY_RUN, default=True): cv.boolean,
        vol.Optional(CONF_CONFIRMATION, default=""): cv.string,
    }
)
SERVICE_DELETE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): _ENTITY_SCHEMA,
        vol.Required(CONF_UID): cv.string,
        vol.Optional(CONF_RECURRENCE_ID): cv.string,
        vol.Optional(CONF_RECURRENCE_RANGE): cv.string,
        vol.Optional(CONF_DRY_RUN, default=True): cv.boolean,
        vol.Optional(CONF_CONFIRMATION, default=""): cv.string,
    }
)
SERVICE_REPLACE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): _ENTITY_SCHEMA,
        vol.Required(CONF_UID): cv.string,
        vol.Required(CONF_SUMMARY): cv.string,
        vol.Required(CONF_START): _DATE_VALUE,
        vol.Required(CONF_END): _DATE_VALUE,
        vol.Optional(CONF_DESCRIPTION, default=""): cv.string,
        vol.Optional(CONF_LOCATION, default=""): cv.string,
        vol.Optional(CONF_RECURRENCE_ID): cv.string,
        vol.Optional(CONF_RECURRENCE_RANGE): cv.string,
        vol.Optional(CONF_DRY_RUN, default=True): cv.boolean,
        vol.Optional(CONF_CONFIRMATION, default=""): cv.string,
    }
)


def _calendar_entity(hass: HomeAssistant, entity_id: str) -> calendar.CalendarEntity:
    """Resolve a calendar entity through the calendar component."""
    component = hass.data.get(calendar.DATA_COMPONENT)
    entity = component.get_entity(entity_id) if component else None
    if not isinstance(entity, calendar.CalendarEntity):
        raise HomeAssistantError(f"Calendar entity not found: {entity_id}")
    return entity


def _window(call: ServiceCall) -> tuple[datetime, datetime]:
    """Return a bounded local-time query window."""
    now = dt_util.now()
    start = call.data.get(CONF_START)
    end = call.data.get(CONF_END)
    if start is None:
        start_datetime = datetime.combine(date(1970, 1, 1), time.min, now.tzinfo)
    elif isinstance(start, datetime):
        start_datetime = dt_util.as_local(start)
    else:
        start_datetime = datetime.combine(start, time.min, now.tzinfo)
    if end is None:
        end_datetime = datetime.combine(date(2100, 1, 1), time.min, now.tzinfo)
    elif isinstance(end, datetime):
        end_datetime = dt_util.as_local(end)
    else:
        end_datetime = datetime.combine(end, time.max, now.tzinfo)
    if start_datetime >= end_datetime:
        raise HomeAssistantError("start must be before end")
    return start_datetime, end_datetime


def _event_dict(event: calendar.CalendarEvent) -> dict[str, Any]:
    """Serialize a calendar event with its UID and recurrence identity."""
    return event.as_dict()


def _matches(event: calendar.CalendarEvent, call: ServiceCall) -> bool:
    """Match summary and/or description using the requested mode."""
    summary = call.data.get(CONF_SUMMARY, "")
    description = call.data.get(CONF_DESCRIPTION, "")
    mode = call.data.get(CONF_MATCH, MATCH_EXACT)
    if not summary and not description:
        raise HomeAssistantError("summary or description is required")

    def match(actual: str | None, expected: str) -> bool:
        if not expected:
            return True
        actual = actual or ""
        if mode == MATCH_CONTAINS:
            return expected.casefold() in actual.casefold()
        return actual == expected

    return match(event.summary, summary) and match(event.description, description)


async def _find_matches(hass: HomeAssistant, call: ServiceCall) -> list[calendar.CalendarEvent]:
    """Fetch and filter calendar events."""
    entity = _calendar_entity(hass, call.data[CONF_ENTITY_ID])
    start, end = _window(call)
    events = await entity.async_get_events(hass, start, end)
    return [event for event in events if _matches(event, call)]


async def _handle_preview(call: ServiceCall) -> ServiceResponse:
    """Return UID-aware matching events without changing the calendar."""
    matches = await _find_matches(call.hass, call)
    start, end = _window(call)
    return {
        "entity_id": call.data[CONF_ENTITY_ID],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(matches),
        "events": [_event_dict(event) for event in matches],
        "mutated": False,
    }


async def _handle_delete(call: ServiceCall) -> ServiceResponse:
    """Delete one UID-aware event, previewing by default."""
    entity_id = call.data[CONF_ENTITY_ID]
    uid = call.data[CONF_UID]
    entity = _calendar_entity(call.hass, entity_id)
    confirmation = f"{CONFIRM_DELETE} {entity_id} {uid}"
    if call.data[CONF_DRY_RUN]:
        return {
            "entity_id": entity_id,
            "uid": uid,
            "recurrence_id": call.data.get(CONF_RECURRENCE_ID),
            "confirmation": confirmation,
            "mutated": False,
        }
    if call.data[CONF_CONFIRMATION] != confirmation:
        raise HomeAssistantError(f"confirmation must exactly equal: {confirmation}")
    await entity.async_delete_event(
        uid,
        recurrence_id=call.data.get(CONF_RECURRENCE_ID),
        recurrence_range=call.data.get(CONF_RECURRENCE_RANGE),
    )
    return {"entity_id": entity_id, "uid": uid, "mutated": True}


async def _handle_delete_matching(call: ServiceCall) -> ServiceResponse:
    """Delete all matching events only after an exact count confirmation."""
    entity_id = call.data[CONF_ENTITY_ID]
    entity = _calendar_entity(call.hass, entity_id)
    matches = await _find_matches(call.hass, call)
    confirmation = f"{CONFIRM_DELETE_MATCHING} {entity_id} {len(matches)}"
    result = {
        "entity_id": entity_id,
        "count": len(matches),
        "events": [_event_dict(event) for event in matches],
        "confirmation": confirmation,
        "mutated": False,
    }
    if call.data[CONF_DRY_RUN]:
        return result
    if call.data[CONF_CONFIRMATION] != confirmation:
        raise HomeAssistantError(f"confirmation must exactly equal: {confirmation}")
    for event in matches:
        await entity.async_delete_event(
            event.uid or "",
            recurrence_id=event.recurrence_id,
            recurrence_range="THISEVENT" if event.recurrence_id else None,
        )
    result["mutated"] = True
    return result


async def _handle_replace(call: ServiceCall) -> ServiceResponse:
    """Replace an event using delete-then-create semantics."""
    entity_id = call.data[CONF_ENTITY_ID]
    uid = call.data[CONF_UID]
    entity = _calendar_entity(call.hass, entity_id)
    confirmation = f"{CONFIRM_REPLACE} {entity_id} {uid}"
    result = {
        "entity_id": entity_id,
        "uid": uid,
        "confirmation": confirmation,
        "mutated": False,
        "warning": "The replacement receives a new UID.",
    }
    if call.data[CONF_DRY_RUN]:
        return result
    if call.data[CONF_CONFIRMATION] != confirmation:
        raise HomeAssistantError(f"confirmation must exactly equal: {confirmation}")
    await entity.async_delete_event(
        uid,
        recurrence_id=call.data.get(CONF_RECURRENCE_ID),
        recurrence_range=call.data.get(CONF_RECURRENCE_RANGE),
    )
    event = {
        "summary": call.data[CONF_SUMMARY],
        "start": call.data[CONF_START],
        "end": call.data[CONF_END],
        "description": call.data[CONF_DESCRIPTION],
        "location": call.data[CONF_LOCATION],
    }
    await entity.async_create_event(**event)
    result["mutated"] = True
    return result


def async_register_services(hass: HomeAssistant) -> None:
    """Register UID-aware calendar services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIEW,
        _handle_preview,
        schema=SERVICE_PREVIEW_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE,
        _handle_delete,
        schema=SERVICE_DELETE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_MATCHING,
        _handle_delete_matching,
        schema=SERVICE_DELETE_MATCHING_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPLACE,
        _handle_replace,
        schema=SERVICE_REPLACE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister UID-aware calendar services."""
    for service in (
        SERVICE_PREVIEW,
        SERVICE_DELETE,
        SERVICE_DELETE_MATCHING,
        SERVICE_REPLACE,
    ):
        hass.services.async_remove(DOMAIN, service)
