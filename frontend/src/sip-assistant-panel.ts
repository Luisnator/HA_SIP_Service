/**
 * SIP Assistant configuration panel.
 *
 * Built with Lit and Home Assistant's own elements (ha-card, ha-form with
 * selectors, ha-button, ha-alert, …) so it follows the active theme.
 */
import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { fetchConfig, navigate } from "./api";
import { createLocalize, type Localize } from "./localize";
import type { HomeAssistant, PanelData, PanelInfo, Route } from "./types";
import "./views/assistants";
import "./views/call-flow";
import "./views/commands";
import "./views/connection";
import "./views/overview";

const TABS = [
  { id: "overview", icon: "mdi:view-dashboard-outline" },
  { id: "commands", icon: "mdi:dialpad" },
  { id: "assistants", icon: "mdi:account-voice" },
  { id: "call", icon: "mdi:phone-settings-outline" },
  { id: "connection", icon: "mdi:lan-connect" },
] as const;

type TabId = (typeof TABS)[number]["id"];

class SipAssistantPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
    _data: { state: true },
    _error: { state: true },
    _loading: { state: true },
  };

  declare hass: HomeAssistant;
  declare narrow: boolean;
  declare route: Route;
  declare panel: PanelInfo;
  declare _data: PanelData | null;
  declare _error: string | null;
  declare _loading: boolean;

  private _localize: Localize = createLocalize("en");
  private _language = "";
  // The integration page links here with ?config_entry=<id>
  private _entryId: string | undefined =
    new URLSearchParams(window.location.search).get("config_entry") ?? undefined;

  constructor() {
    super();
    this.narrow = false;
    this._data = null;
    this._error = null;
    this._loading = true;
  }

  private get _tab(): TabId {
    const segment = this.route?.path?.split("/")[1] ?? "";
    return (TABS.find((tab) => tab.id === segment)?.id ?? "overview") as TabId;
  }

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("hass") && this.hass) {
      const language = this.hass.locale?.language ?? this.hass.language;
      if (language !== this._language) {
        this._language = language;
        this._localize = createLocalize(language);
      }
      if (!changed.get("hass")) this._load();
    }
    if (changed.has("route") && changed.get("route") && this._tab === "overview" && this.hass) {
      this._load();
    }
  }

  private async _load(): Promise<void> {
    try {
      this._data = await fetchConfig(this.hass, this._entryId);
      this._entryId = this._data?.entry_id;
      this._error = null;
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private _goTo(tab: string): void {
    const base = `/${this.panel?.url_path ?? "sip-assistant"}`;
    navigate(tab === "overview" ? base : `${base}/${tab}`);
  }

  protected render(): TemplateResult {
    const localize = this._localize;
    return html`
      <div class="header">
        <div class="toolbar">
          <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
          <div class="main-title">${this.panel?.title ?? "SIP Assistant"}</div>
          ${this._data && this._data.entries.length > 1
            ? html`<select class="entry-select" @change=${this._entryChanged}>
                ${this._data.entries.map(
                  (entry) =>
                    html`<option value=${entry.entry_id} ?selected=${entry.entry_id === this._data!.entry_id}>
                      ${entry.title}
                    </option>`,
                )}
              </select>`
            : nothing}
        </div>
        ${this._data
          ? html`<nav class="tabs" role="tablist">
              ${TABS.map(
                (tab) => html`
                  <button
                    role="tab"
                    class="tab ${tab.id === this._tab ? "active" : ""}"
                    aria-selected=${tab.id === this._tab}
                    @click=${() => this._goTo(tab.id)}
                  >
                    <ha-icon .icon=${tab.icon}></ha-icon>
                    <span>${localize(`tabs.${tab.id}`)}</span>
                  </button>
                `,
              )}
            </nav>`
          : nothing}
      </div>
      <div
        class="content ${this.narrow ? "narrow" : ""}"
        @config-changed=${(ev: CustomEvent) => (this._data = ev.detail.config)}
        @navigate-tab=${(ev: CustomEvent) => this._goTo(ev.detail.tab)}
      >
        ${this._renderContent()}
      </div>
    `;
  }

  private _renderContent(): TemplateResult {
    const localize = this._localize;
    if (this._loading) {
      return html`<div class="message"><ha-spinner></ha-spinner>${localize("common.loading")}</div>`;
    }
    if (this._error) {
      return html`<ha-alert alert-type="error" .title=${localize("common.error_loading")}>${this._error}</ha-alert>`;
    }
    if (!this._data) {
      return html`<ha-alert alert-type="info">${localize("common.no_entry")}</ha-alert>`;
    }
    const props = { hass: this.hass, data: this._data, localize, narrow: this.narrow };
    switch (this._tab) {
      case "commands":
        return html`<sip-assistant-commands
          .hass=${props.hass}
          .data=${props.data}
          .localize=${localize}
          .narrow=${props.narrow}
        ></sip-assistant-commands>`;
      case "assistants":
        return html`<sip-assistant-assistants
          .hass=${props.hass}
          .data=${props.data}
          .localize=${localize}
          .narrow=${props.narrow}
        ></sip-assistant-assistants>`;
      case "call":
        return html`<sip-assistant-call-flow
          .hass=${props.hass}
          .data=${props.data}
          .localize=${localize}
          .narrow=${props.narrow}
        ></sip-assistant-call-flow>`;
      case "connection":
        return html`<sip-assistant-connection
          .hass=${props.hass}
          .data=${props.data}
          .localize=${localize}
          .narrow=${props.narrow}
        ></sip-assistant-connection>`;
      default:
        return html`<sip-assistant-overview
          .hass=${props.hass}
          .data=${props.data}
          .localize=${localize}
          .narrow=${props.narrow}
        ></sip-assistant-overview>`;
    }
  }

  private async _entryChanged(ev: Event): Promise<void> {
    this._entryId = (ev.target as HTMLSelectElement).value;
    this._loading = true;
    await this._load();
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--ha-font-family-body, Roboto, sans-serif);
    }
    .header {
      position: sticky;
      top: 0;
      z-index: 4;
      background: var(--app-header-background-color);
      color: var(--app-header-text-color, white);
      border-bottom: var(--app-header-border-bottom, none);
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      height: var(--header-height, 56px);
      padding: 0 12px;
      box-sizing: border-box;
    }
    .main-title {
      flex: 1;
      margin-inline-start: 8px;
      font-size: 20px;
      font-weight: 400;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .entry-select {
      max-width: 40%;
      padding: 6px 8px;
      border-radius: 8px;
      border: 1px solid currentColor;
      background: transparent;
      color: inherit;
      font: inherit;
    }
    .entry-select option {
      color: var(--primary-text-color);
      background: var(--card-background-color);
    }
    .tabs {
      display: flex;
      gap: 4px;
      padding: 0 8px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .tab {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px 12px;
      border: none;
      border-bottom: 2px solid transparent;
      background: none;
      color: inherit;
      opacity: 0.75;
      font: inherit;
      font-size: 14px;
      font-weight: 500;
      white-space: nowrap;
      cursor: pointer;
    }
    .tab ha-icon {
      --mdc-icon-size: 20px;
    }
    .tab:hover {
      opacity: 1;
    }
    .tab.active {
      opacity: 1;
      border-bottom-color: currentColor;
    }
    .content {
      max-width: 1240px;
      margin: 0 auto;
      padding: 16px;
      box-sizing: border-box;
    }
    .content.narrow {
      padding: 8px;
    }
    .message {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 48px;
      color: var(--secondary-text-color);
    }
  `;
}

if (!customElements.get("sip-assistant-panel")) {
  customElements.define("sip-assistant-panel", SipAssistantPanel);
}
