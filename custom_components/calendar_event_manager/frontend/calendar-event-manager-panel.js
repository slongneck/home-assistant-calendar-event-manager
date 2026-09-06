import "/calendar_event_manager/calendar-event-manager.js?v=1.0.1";

class CalendarEventManagerPanel extends HTMLElement {
  connectedCallback() {
    if (this._manager) return;
    this._manager = document.createElement("calendar-event-manager");
    this._manager.setConfig({ title: "Calendar Event Manager" });
    this.appendChild(this._manager);
    if (this._hass) this._manager.hass = this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._manager) this._manager.hass = hass;
  }

  set narrow(narrow) {
    this._narrow = narrow;
  }

  set panel(panel) {
    this._panel = panel;
  }
}

customElements.define("calendar-event-manager-panel", CalendarEventManagerPanel);
