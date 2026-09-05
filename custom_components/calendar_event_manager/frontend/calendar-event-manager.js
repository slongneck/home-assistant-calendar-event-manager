class CalendarEventManager extends HTMLElement {
  setConfig(config) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.config = {
      calendars: [],
      selected_calendar_entity: null,
      selected_series_entity: null,
      ...config,
    };
    this._events = [];
    this._calendarOptions = this.config.calendars;
    this._calendarsLoaded = false;
    this._selected = new Set();
    this._type = "*";
    this._calendar = this.config.calendars[0];
    this._start = this._dateString(new Date());
    this._end = this._dateString(new Date(Date.now() + 14 * 86400000));
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._calendarsLoaded) this._loadCalendars();
  }

  getCardSize() {
    return 8;
  }

  _dateString(date) {
    return date.toISOString().slice(0, 10);
  }

  _eventValue(event, field) {
    return event?.[field]?.dateTime || event?.[field]?.date || "";
  }

  _eventType(event) {
    return event.description || event.summary || "(untitled)";
  }

  _visibleEvents() {
    if (this._type === "*") return this._events;
    return this._events.filter((event) => this._eventType(event) === this._type);
  }

  async _loadCalendars() {
    if (!this._hass) return;
    this._calendarsLoaded = true;
    try {
      const calendars = await this._hass.callApi("GET", "calendars");
      this._calendarOptions = calendars.map((calendar) => calendar.entity_id);
      if (!this._calendarOptions.includes(this._calendar)) {
        this._calendar = this._calendarOptions[0] || "";
      }
      this._render();
    } catch (error) {
      this._status = `Unable to discover calendars: ${error.message || error}`;
      this._render();
    }
  }

  async _loadEvents() {
    if (!this._hass) return;
    this._status = "Loading calendar events...";
    this._render();
    try {
      const query = new URLSearchParams({
        start: `${this._start}T00:00:00`,
        end: `${this._end}T23:59:59`,
      });
      this._events = await this._hass.callApi(
        "GET",
        `calendars/${this._calendar}?${query.toString()}`,
      );
      this._selected.clear();
      this._status = `${this._events.length} event(s) found. No changes made.`;
    } catch (error) {
      this._events = [];
      this._status = `Unable to read calendar: ${error.message || error}`;
    }
    this._render();
  }

  _eventId(event, index) {
    return `${event.uid || "event"}-${event.recurrence_id || index}`;
  }

  _selectedEvents() {
    return this._visibleEvents().filter((event, index) =>
      this._selected.has(this._eventId(event, index)),
    );
  }

  async _deleteSelected() {
    const events = this._selectedEvents();
    if (!events.length) return;
    if (!window.confirm(`Delete ${events.length} selected calendar event(s)?`)) return;
    this._status = "Deleting selected events...";
    this._render();
    try {
      for (const event of events) {
        const message = {
          type: "calendar/event/delete",
          entity_id: this._calendar,
          uid: event.uid,
        };
        if (event.recurrence_id) {
          message.recurrence_id = event.recurrence_id;
          message.recurrence_range = "THISEVENT";
        }
        await this._hass.callWS(message);
      }
      this._status = `${events.length} event(s) deleted.`;
      await this._loadEvents();
    } catch (error) {
      this._status = `Delete failed: ${error.message || error}`;
      this._render();
    }
  }

  async _deleteSeriesSelected() {
    const events = this._selectedEvents();
    if (events.length !== 1 || !events[0].rrule) {
      this._status = "Select exactly one recurring event to delete its series.";
      this._render();
      return;
    }
    const event = events[0];
    const confirmation = `DELETE SERIES ${this._calendar} ${event.uid}`;
    if (!window.confirm("Delete the entire recurring series? This removes all occurrences.")) return;
    try {
      await this._hass.callService("calendar_event_manager", "delete_series", {
        entity_id: this._calendar,
        uid: event.uid,
        dry_run: false,
        confirmation,
      });
      this._status = "Recurring series deleted.";
      await this._loadEvents();
    } catch (error) {
      this._status = `Series deletion failed: ${error.message || error}`;
      this._render();
    }
  }

  async _editSelected() {
    const events = this._selectedEvents();
    if (events.length !== 1) {
      this._status = "Select exactly one event to edit.";
      this._render();
      return;
    }
    const event = events[0];
    const summary = this.shadowRoot.querySelector("[data-edit-summary]").value;
    const start = this.shadowRoot.querySelector("[data-edit-start]").value;
    const end = this.shadowRoot.querySelector("[data-edit-end]").value;
    const description = this.shadowRoot.querySelector("[data-edit-description]").value;
    if (!summary || !start || !end) {
      this._status = "Summary, start, and end are required for editing.";
      this._render();
      return;
    }
    if (!window.confirm("Replace this event? The original will be deleted first.")) return;
    this._status = "Replacing event...";
    this._render();
    try {
      const deleteMessage = {
        type: "calendar/event/delete",
        entity_id: this._calendar,
        uid: event.uid,
      };
      if (event.recurrence_id) {
        deleteMessage.recurrence_id = event.recurrence_id;
        deleteMessage.recurrence_range = "THISEVENT";
      }
      await this._hass.callWS(deleteMessage);
      await this._hass.callService("calendar", "create_event", {
        entity_id: this._calendar,
        summary,
        description,
        start_date_time: new Date(start).toISOString(),
        end_date_time: new Date(end).toISOString(),
      });
      this._status = "Event replaced. The replacement has a new UID.";
      await this._loadEvents();
    } catch (error) {
      this._status = `Edit failed: ${error.message || error}`;
      this._render();
    }
  }

  async _createEvent() {
    const summary = this.shadowRoot.querySelector("[data-create-summary]").value;
    const start = this.shadowRoot.querySelector("[data-create-start]").value;
    const end = this.shadowRoot.querySelector("[data-create-end]").value;
    const description = this.shadowRoot.querySelector("[data-create-description]").value;
    if (!summary || !start || !end) {
      this._status = "Summary, start, and end are required for creation.";
      this._render();
      return;
    }
    if (!window.confirm("Create this calendar event?")) return;
    try {
      await this._hass.callService("calendar", "create_event", {
        entity_id: this._calendar,
        summary,
        description,
        start_date_time: new Date(start).toISOString(),
        end_date_time: new Date(end).toISOString(),
      });
      this._status = "Event created.";
      await this._loadEvents();
    } catch (error) {
      this._status = `Create failed: ${error.message || error}`;
      this._render();
    }
  }

  _setSelected(event, checked, index) {
    const id = this._eventId(event, index);
    if (checked) this._selected.add(id);
    else this._selected.delete(id);
    if (this._hass && this.config.selected_calendar_entity) {
      this._hass.callService("input_text", "set_value", {
        entity_id: this.config.selected_calendar_entity,
        value: this._calendar,
      }).catch(() => {});
    }
    if (this._hass && this.config.selected_series_entity) {
      const selected = this._selectedEvents();
      const value = selected.length === 1
        ? `${selected[0].summary || "(untitled)"} | UID ${selected[0].uid || "unknown"}`
        : "No single event selected";
      this._hass.callService("input_text", "set_value", {
        entity_id: this.config.selected_series_entity,
        value: value.slice(0, 255),
      }).catch(() => {});
    }
    this._render();
  }

  _render() {
    if (!this.config) return;
    const types = [...new Set(this._events.map((event) => this._eventType(event)))].sort();
    const visible = this._visibleEvents();
    const selected = this._selectedEvents();
    const selectedEvent = selected.length === 1 ? selected[0] : null;
    const toLocalInput = (value) => value?.dateTime ? value.dateTime.slice(0, 16) : "";
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .card-content { padding: 16px; }
        h2 { margin: 0 0 12px; font-size: 1.2rem; }
        .controls, .form { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
        label { display: grid; gap: 4px; font-size: .85rem; }
        input, select, textarea, button { box-sizing: border-box; font: inherit; padding: 7px; }
        textarea { min-height: 60px; resize: vertical; }
        button { cursor: pointer; }
        button:disabled { cursor: not-allowed; opacity: .5; }
        .actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
        .status { color: var(--secondary-text-color); min-height: 1.2em; }
        .events { display: grid; gap: 8px; max-height: 360px; overflow: auto; }
        .event { align-items: start; background: var(--secondary-background-color); border-radius: 8px; display: flex; gap: 8px; padding: 8px; }
        .event input { margin-top: 3px; }
        details { margin-top: 12px; }
        summary { cursor: pointer; font-weight: 600; padding: 8px 0; }
        small { color: var(--secondary-text-color); }
      </style>
      <ha-card>
        <div class="card-content">
          <h2>${this.config.title || "Calendar Event Manager"}</h2>
          <div class="controls">
            <label>Calendar<select data-calendar>${this._calendarOptions.map((calendar) => `<option value="${calendar}" ${calendar === this._calendar ? "selected" : ""}>${calendar.replace("calendar.", "")}</option>`).join("")}</select></label>
            <label>Event type<select data-type><option value="*">All event types</option>${types.map((type) => `<option value="${this._escape(type)}" ${type === this._type ? "selected" : ""}>${this._escape(type)}</option>`).join("")}</select></label>
            <label>Start<input type="date" data-start value="${this._start}"></label>
            <label>End<input type="date" data-end value="${this._end}"></label>
          </div>
          <div class="actions"><button data-load>Preview</button><button data-delete ${selected.length ? "" : "disabled"}>Delete selected occurrence(s)</button><button data-delete-series ${selected.length === 1 && selectedEvent?.rrule ? "" : "disabled"}>Delete recurring series</button></div>
          <p class="status">${this._status || "Preview is read-only until an action is confirmed."}</p>
          <div class="events">${visible.length ? visible.map((event, index) => `<label class="event"><input type="checkbox" data-event="${index}" ${this._selected.has(this._eventId(event, index)) ? "checked" : ""}><span><strong>${this._escape(event.summary || "(untitled)")}</strong><br>${this._escape(this._eventValue(event, "start"))} - ${this._escape(this._eventValue(event, "end"))}<br><small>${this._escape(event.description || "")}</small></span></label>`).join("") : "<p>No events loaded. Choose a calendar and press Preview.</p>"}</div>
          <details><summary>Edit selected event</summary><div class="form"><label>Summary<input data-edit-summary value="${this._escape(selectedEvent?.summary || "")}"></label><label>Start<input type="datetime-local" data-edit-start value="${toLocalInput(selectedEvent?.start)}"></label><label>End<input type="datetime-local" data-edit-end value="${toLocalInput(selectedEvent?.end)}"></label><label>Description<textarea data-edit-description>${this._escape(selectedEvent?.description || "")}</textarea></label><button data-edit ${selected.length === 1 ? "" : "disabled"}>Replace selected</button></div></details>
          <details><summary>Create event</summary><div class="form"><label>Summary<input data-create-summary></label><label>Start<input type="datetime-local" data-create-start></label><label>End<input type="datetime-local" data-create-end></label><label>Description<textarea data-create-description></textarea></label><button data-create>Create event</button></div></details>
        </div>
      </ha-card>`;
    this._bind();
  }

  _escape(value) {
    return String(value || "").replace(/[&<>\"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[character]);
  }

  _bind() {
    this.shadowRoot?.querySelector("[data-calendar]")?.addEventListener("change", (event) => { this._calendar = event.target.value; });
    this.shadowRoot?.querySelector("[data-type]")?.addEventListener("change", (event) => { this._type = event.target.value; this._render(); });
    this.shadowRoot?.querySelector("[data-start]")?.addEventListener("change", (event) => { this._start = event.target.value; });
    this.shadowRoot?.querySelector("[data-end]")?.addEventListener("change", (event) => { this._end = event.target.value; });
    this.shadowRoot?.querySelector("[data-load]")?.addEventListener("click", () => this._loadEvents());
    this.shadowRoot?.querySelector("[data-delete]")?.addEventListener("click", () => this._deleteSelected());
    this.shadowRoot?.querySelector("[data-delete-series]")?.addEventListener("click", () => this._deleteSeriesSelected());
    this.shadowRoot?.querySelector("[data-edit]")?.addEventListener("click", () => this._editSelected());
    this.shadowRoot?.querySelector("[data-create]")?.addEventListener("click", () => this._createEvent());
    this.shadowRoot?.querySelectorAll("[data-event]").forEach((input) => input.addEventListener("change", (event) => this._setSelected(visibleEvent(this._visibleEvents(), Number(event.target.dataset.event)), event.target.checked, Number(event.target.dataset.event))));
  }
}

function visibleEvent(events, index) {
  return events[index];
}

customElements.define("calendar-event-manager", CalendarEventManager);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "calendar-event-manager",
  name: "Calendar Event Manager",
  description: "Preview, create, edit, and delete calendar events with confirmation.",
});
