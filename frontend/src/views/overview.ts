import { LitElement, css, html, nothing, type TemplateResult } from "lit";

import { copyToClipboard, showToast } from "../api";
import type { Localize } from "../localize";
import { sharedStyles } from "../styles";
import type { Assistant, Command, HomeAssistant, PanelData } from "../types";
import { isRisky } from "./assistants";
import { byCode, fireNavigate } from "./helpers";

const COMMAND_ICONS: Record<string, string> = {
  entity: "mdi:play-circle-outline",
  actions: "mdi:format-list-bulleted-square",
  announcement: "mdi:account-voice",
};

interface Check {
  type: "warning" | "info" | "error";
  text: string;
  tab?: string;
  action?: string;
}

export class SipOverviewView extends LitElement {
  static properties = {
    hass: { attribute: false },
    data: { attribute: false },
    localize: { attribute: false },
    narrow: { type: Boolean },
  };

  static styles = [
    sharedStyles,
    css`
      .grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 16px;
        align-items: start;
      }
      .grid.narrow {
        grid-template-columns: minmax(0, 1fr);
      }
      .status {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 8px 16px 16px;
      }
      .status-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: rgba(var(--rgb-primary-color), 0.14);
        color: var(--primary-color);
        flex-shrink: 0;
      }
      .status-icon.busy {
        background: rgba(var(--rgb-success-color, 67, 160, 71), 0.18);
        color: var(--success-color);
      }
      .status-icon.down {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color);
      }
      .status-icon ha-icon {
        --mdc-icon-size: 28px;
      }
      .status-text .state {
        font-size: 22px;
        font-weight: 500;
      }
      .status-text .detail {
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .facts {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        gap: 8px 16px;
        padding: 0 16px 16px;
        align-items: center;
      }
      .facts .label {
        color: var(--secondary-text-color);
      }
      .uri {
        display: flex;
        align-items: center;
        gap: 4px;
        min-width: 0;
      }
      .uri code {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 15px;
        user-select: all;
      }
      .keypad-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 16px;
      }
      .keypad-row ha-icon.type {
        color: var(--secondary-text-color);
        --mdc-icon-size: 20px;
      }
      .keypad-row .text {
        flex: 1;
        min-width: 0;
      }
      .keypad-row .name {
        font-size: 15px;
      }
      .keypad-row .detail {
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .keypad-row.unreachable {
        opacity: 0.55;
      }
      .start {
        margin: 0 16px 8px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--secondary-background-color);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .divider {
        height: 1px;
        margin: 8px 16px;
        background: var(--divider-color);
      }
    `,
  ];

  declare hass: HomeAssistant;
  declare data: PanelData;
  declare localize: Localize;
  declare narrow: boolean;

  protected render(): TemplateResult {
    return html`
      <div class="grid ${this.narrow ? "narrow" : ""}">
        <div>${this._renderStatus()} ${this._renderChecks()}</div>
        <div>${this._renderKeypad()}</div>
      </div>
    `;
  }

  private _state(key: string) {
    const entityId = this.data.info.entities[key];
    return entityId ? this.hass.states[entityId] : undefined;
  }

  private _renderStatus(): TemplateResult {
    const callState = this._state("call_state");
    const running = this.data.loaded && callState !== undefined && callState.state !== "unavailable";
    const phase = running ? callState!.state : "unavailable";
    const activeCalls = Number(callState?.attributes.active_calls ?? 0);
    const lastCaller = this._state("last_caller");
    const lastCall = this._state("last_call");
    const uri = this.data.info.sip_uri;
    const icon = !running ? "mdi:phone-off" : activeCalls ? "mdi:phone-in-talk" : "mdi:phone-check";
    return html`
      <ha-card>
        <div class="card-header">${this.localize("overview.status")}</div>
        <div class="status">
          <div class="status-icon ${!running ? "down" : activeCalls ? "busy" : ""}">
            <ha-icon .icon=${icon}></ha-icon>
          </div>
          <div class="status-text">
            <div class="state">${this.localize(`state.${phase}`)}</div>
            <div class="detail">
              ${activeCalls
                ? html`${this.localize("overview.active_calls")}: ${activeCalls}
                  ${callState?.attributes.caller_name || callState?.attributes.caller || ""}`
                : this.localize("overview.how_to")}
            </div>
          </div>
        </div>
        <div class="facts">
          <span class="label">${this.localize("overview.sip_address")}</span>
          <span class="uri">
            <code>${uri ?? "–"}</code>
            ${uri
              ? html`<button class="icon-button" title=${this.localize("overview.copy")} @click=${this._copy}>
                  <ha-icon icon="mdi:content-copy"></ha-icon>
                </button>`
              : nothing}
          </span>
          <span class="label">${this.localize("overview.last_caller")}</span>
          <span>${lastCaller && lastCaller.state !== "unknown" ? lastCaller.state : this.localize("overview.never")}</span>
          <span class="label">${this.localize("overview.last_call")}</span>
          <span>${lastCall && lastCall.state !== "unknown" ? this._formatTime(lastCall.state) : "–"}</span>
        </div>
        ${activeCalls
          ? html`<div class="card-actions">
              <ha-button variant="danger" appearance="filled" @click=${this._hangUp}>
                <ha-icon slot="start" icon="mdi:phone-hangup"></ha-icon>
                ${this.localize("overview.hang_up")}
              </ha-button>
            </div>`
          : nothing}
      </ha-card>
    `;
  }

  private _checks(): Check[] {
    const checks: Check[] = [];
    const { data } = this;
    if (!data.loaded) checks.push({ type: "error", text: this.localize("common.not_loaded") });
    if (data.assistants.length && !data.connection.has_api_key) {
      checks.push({
        type: "warning",
        text: this.localize("overview.check_no_api_key"),
        tab: "connection",
        action: "overview.go_connection",
      });
    }
    for (const assistant of data.assistants.filter(isRisky)) {
      checks.push({
        type: "warning",
        text: this.localize("overview.check_risky", { name: assistant.name }),
        tab: "assistants",
        action: "overview.go_assistants",
      });
    }
    if (!data.connection.has_sip_password && !data.network.allowed_networks?.trim()) {
      checks.push({
        type: "warning",
        text: this.localize("overview.check_open"),
        tab: "connection",
        action: "overview.go_connection",
      });
    }
    if (data.loaded && !data.info.tts_engine) {
      checks.push({ type: "info", text: this.localize("overview.check_no_tts") });
    }
    if (!data.commands.length && !data.assistants.length) {
      checks.push({
        type: "info",
        text: this.localize("overview.check_nothing"),
        tab: "commands",
        action: "overview.go_commands",
      });
    }
    return checks;
  }

  private _renderChecks(): TemplateResult {
    const checks = this._checks();
    return html`
      <ha-card>
        <div class="card-header">${this.localize("overview.checks")}</div>
        <div class="card-content">
          ${checks.length === 0
            ? html`<ha-alert alert-type="success">${this.localize("overview.all_good")}</ha-alert>`
            : checks.map(
                (check) => html`<ha-alert .alertType=${check.type}>
                  ${check.text}
                  ${check.tab
                    ? html`<ha-button
                        slot="action"
                        appearance="plain"
                        size="small"
                        @click=${() => fireNavigate(this, check.tab!)}
                        >${this.localize(check.action!)}</ha-button
                      >`
                    : nothing}
                </ha-alert>`,
              )}
        </div>
      </ha-card>
    `;
  }

  private _renderKeypad(): TemplateResult {
    const { data } = this;
    const start = data.assistants.find((assistant) => assistant.id === data.call.start);
    const items = byCode<Command | Assistant>([...data.commands, ...data.assistants]);
    return html`
      <ha-card>
        <div class="card-header">${this.localize("overview.keypad")}</div>
        <div class="card-subtitle">${this.localize("overview.keypad_hint")}</div>
        <div class="start">
          <ha-icon icon="mdi:phone-incoming"></ha-icon>
          <span>${this.localize("overview.starts_with")} <b>${start ? start.name : this.localize("overview.start_menu")}</b></span>
        </div>
        ${items.map((item) => this._renderKey(item))}
        <div class="divider"></div>
        <div class="keypad-row">
          <span class="code fixed">*</span>
          <span class="text"><div class="name">${this.localize("overview.key_repeat")}</div></span>
        </div>
        <div class="keypad-row">
          <span class="code fixed">#</span>
          <span class="text"><div class="name">${this.localize("overview.key_submit")}</div></span>
        </div>
        <div style="height: 8px"></div>
      </ha-card>
    `;
  }

  private _renderKey(item: Command | Assistant): TemplateResult {
    const isAssistant = "engine" in item;
    const unreachable = isAssistant && !this.data.connection.has_api_key;
    const icon = isAssistant ? "mdi:account-voice" : COMMAND_ICONS[(item as Command).action_type];
    const detail = isAssistant
      ? this.localize(`assistants.engine_${(item as Assistant).engine}`)
      : this.localize(`commands.type_${(item as Command).action_type}`);
    return html`
      <div class="keypad-row ${unreachable ? "unreachable" : ""}">
        <span class="code">${item.code}</span>
        <ha-icon class="type" .icon=${icon}></ha-icon>
        <span class="text">
          <div class="name">${item.name}</div>
          <div class="detail">
            ${detail} ·
            ${unreachable
              ? this.localize("overview.unreachable")
              : this.localize(item.announce ? "overview.announced" : "overview.not_announced")}
          </div>
        </span>
        ${isAssistant && isRisky(item as Assistant)
          ? html`<ha-icon icon="mdi:alert-outline" style="color: var(--warning-color)"></ha-icon>`
          : nothing}
      </div>
    `;
  }

  private _formatTime(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(this.hass.locale?.language ?? this.hass.language, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  private async _copy(): Promise<void> {
    if (!this.data.info.sip_uri) return;
    await copyToClipboard(this.data.info.sip_uri);
    showToast(this, this.localize("overview.copied"));
  }

  private async _hangUp(): Promise<void> {
    const entityId = this.data.info.entities.hang_up;
    if (entityId) await this.hass.callService("button", "press", { entity_id: entityId });
  }
}

if (!customElements.get("sip-assistant-overview")) {
  customElements.define("sip-assistant-overview", SipOverviewView);
}
