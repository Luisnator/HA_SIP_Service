import { LitElement, html, nothing, type TemplateResult } from "lit";

import { deleteItem, saveItem, showToast } from "../api";
import type { Localize } from "../localize";
import { sharedStyles } from "../styles";
import type { Assistant, Engine, FormSchema, HomeAssistant, PanelData } from "../types";
import {
  byCode,
  fireConfigChanged,
  fireNavigate,
  isDirty,
  nextFreeCode,
  translateErrors,
} from "./helpers";

const ENGINES: { engine: Engine; icon: string }[] = [
  { engine: "live", icon: "mdi:account-voice" },
  { engine: "realtime", icon: "mdi:waveform" },
];

type Toggle = "home_control" | "phone_commands" | "web_search" | "fast_interrupt";

export const isRisky = (assistant: Assistant): boolean =>
  assistant.web_search &&
  ((assistant.home_control && assistant.llm_hass_api.length > 0) || assistant.phone_commands);

export class SipAssistantsView extends LitElement {
  static properties = {
    hass: { attribute: false },
    data: { attribute: false },
    localize: { attribute: false },
    narrow: { type: Boolean },
    _selected: { state: true },
    _draft: { state: true },
    _errors: { state: true },
    _saving: { state: true },
    _confirmDelete: { state: true },
  };

  static styles = sharedStyles;

  declare hass: HomeAssistant;
  declare data: PanelData;
  declare localize: Localize;
  declare narrow: boolean;
  declare _selected: string | null;
  declare _draft: Assistant | null;
  declare _errors: Record<string, string>;
  declare _saving: boolean;
  declare _confirmDelete: boolean;

  constructor() {
    super();
    this.narrow = false;
    this._selected = null;
    this._draft = null;
    this._errors = {};
    this._saving = false;
    this._confirmDelete = false;
  }

  private get _original(): Assistant | undefined {
    return this.data.assistants.find((assistant) => assistant.id === this._selected);
  }

  protected render(): TemplateResult {
    const showList = !this.narrow || this._selected === null;
    const showEditor = !this.narrow || this._selected !== null;
    return html`
      <div class="master-detail ${this.narrow ? "narrow" : ""}">
        ${showList ? this._renderList() : nothing}
        ${showEditor ? this._renderEditor() : nothing}
      </div>
    `;
  }

  private _badges(assistant: Assistant): TemplateResult {
    const home = assistant.home_control && assistant.llm_hass_api.length > 0;
    return html`
      <div class="badges">
        ${assistant.id === this.data.call.start
          ? html`<span class="badge accent"
              ><ha-icon icon="mdi:phone-in-talk"></ha-icon>${this.localize("assistants.starts_calls")}</span
            >`
          : nothing}
        ${home
          ? html`<span class="badge"
              ><ha-icon icon="mdi:home-automation"></ha-icon>${this.localize("assistants.badge_home")}</span
            >`
          : nothing}
        ${assistant.phone_commands
          ? html`<span class="badge"
              ><ha-icon icon="mdi:dialpad"></ha-icon>${this.localize("assistants.badge_commands")}</span
            >`
          : nothing}
        ${assistant.web_search
          ? html`<span class="badge ${isRisky(assistant) ? "warning" : ""}"
              ><ha-icon icon=${isRisky(assistant) ? "mdi:alert-outline" : "mdi:web"}></ha-icon>${this.localize(
                "assistants.badge_web",
              )}</span
            >`
          : nothing}
        ${!home && !assistant.phone_commands && !assistant.web_search
          ? html`<span class="badge"
              ><ha-icon icon="mdi:chat-outline"></ha-icon>${this.localize("assistants.badge_talk")}</span
            >`
          : nothing}
      </div>
    `;
  }

  private _renderList(): TemplateResult {
    const assistants = byCode(this.data.assistants);
    return html`
      <ha-card>
        <div class="card-header">
          <span>${this.localize("tabs.assistants")}</span>
          <ha-button appearance="filled" size="small" @click=${this._new}>
            <ha-icon slot="start" icon="mdi:plus"></ha-icon>
            ${this.localize("assistants.add")}
          </ha-button>
        </div>
        ${!this.data.connection.has_api_key && assistants.length
          ? html`<div class="card-content">
              <ha-alert alert-type="warning">${this.localize("assistants.no_api_key")}</ha-alert>
            </div>`
          : nothing}
        <div class="list">
          ${assistants.length === 0
            ? html`<div class="empty">${this.localize("assistants.empty")}</div>`
            : assistants.map(
                (assistant) => html`
                  <button
                    class="list-item ${assistant.id === this._selected ? "selected" : ""}"
                    @click=${() => this._select(assistant)}
                  >
                    <span class="code">${assistant.code}</span>
                    <span class="text">
                      <div class="primary">${assistant.name}</div>
                      <div class="secondary">
                        ${this.localize(`assistants.engine_${assistant.engine}`)} · ${assistant.voice}
                      </div>
                      ${this._badges(assistant)}
                    </span>
                  </button>
                `,
              )}
        </div>
      </ha-card>
    `;
  }

  private _renderEditor(): TemplateResult {
    if (this._draft === null) {
      return html`
        <ha-card>
          <div class="placeholder">
            <ha-icon icon="mdi:account-voice"></ha-icon>
            <div>${this.localize("assistants.select")}</div>
          </div>
        </ha-card>
      `;
    }
    const draft = this._draft;
    const dirty = isDirty(draft, this._original);
    const errors = translateErrors(this._errors, this.localize);
    return html`
      <ha-card>
        <div class="editor-header">
          ${this.narrow
            ? html`<button class="icon-button" @click=${this._close} title=${this.localize("common.back")}>
                <ha-icon icon="mdi:arrow-left"></ha-icon>
              </button>`
            : nothing}
          <span class="code">${draft.code || "?"}</span>
          <span class="title">${draft.name || this.localize("assistants.new")}</span>
        </div>
        <div class="card-content">
          ${!this.data.connection.has_api_key
            ? html`<ha-alert alert-type="warning">
                ${this.localize("assistants.no_api_key")}
                <ha-button slot="action" appearance="plain" size="small" @click=${() => fireNavigate(this, "connection")}
                  >${this.localize("overview.go_connection")}</ha-button
                >
              </ha-alert>`
            : nothing}

          <div class="section-title">${this.localize("assistants.general")}</div>
          ${this._form(
            [
              { name: "name", required: true, selector: { text: {} } },
                  { name: "code", required: true, selector: { text: {} } },
              { name: "announce", selector: { boolean: {} } },
            ],
            errors,
          )}

          <div class="section-title">${this.localize("assistants.model")}</div>
          <div class="tiles">
            ${ENGINES.map(
              ({ engine, icon }) => html`
                <button
                  class="tile ${draft.engine === engine ? "selected" : ""}"
                  @click=${() => this._update({ engine })}
                >
                  <span class="tile-title"><ha-icon .icon=${icon}></ha-icon>${this.localize(
                    `assistants.engine_${engine}`,
                  )}</span>
                  <span class="tile-desc">${this.localize(`assistants.engine_${engine}_desc`)}</span>
                </button>
              `,
            )}
          </div>
          ${this._form(
            [
              {
                name: "voice",
                required: true,
                selector: {
                  select: { options: this.data.info.voices, custom_value: true, mode: "dropdown" },
                },
              },
              { name: "prompt", selector: { template: {} } },
            ],
            errors,
          )}

          <div class="section-title">${this.localize("assistants.access")}</div>
          ${this._switch("home_control", "mdi:home-automation")}
          ${draft.home_control
            ? html`<div class="nested">
                ${this._form(
                  [
                    {
                      name: "llm_hass_api",
                      selector: {
                        select: {
                          multiple: true,
                          mode: "list",
                          options: this.data.info.llm_apis.map((api) => ({
                            value: api.id,
                            label: api.name,
                          })),
                        },
                      },
                    },
                  ],
                  errors,
                )}
              </div>`
            : nothing}
          ${this._switch("phone_commands", "mdi:dialpad")} ${this._switch("web_search", "mdi:web")}
          ${isRisky(draft)
            ? html`<ha-alert alert-type="warning" .title=${this.localize("assistants.risky_title")}>
                ${this.localize("assistants.risky_text")}
              </ha-alert>`
            : nothing}

          <div class="section-title">${this.localize("assistants.behaviour")}</div>
          ${this._switch("fast_interrupt", "mdi:hand-back-left-outline")}

          <ha-expansion-panel outlined .header=${this.localize("assistants.advanced")}>
            ${this._form(
              draft.engine === "live"
                ? [
                    this._modelField("live_model", this.data.info.live_models),
                    this._modelField("backend_model", this.data.info.backend_models),
                    {
                      name: "reasoning_effort",
                      selector: {
                        select: {
                          mode: "dropdown",
                          options: this.data.info.reasoning_efforts.map((effort) => ({
                            value: effort,
                            label: this.localize(`assistants.effort.${effort}`),
                          })),
                        },
                      },
                    },
                  ]
                : [
                    this._modelField("realtime_model", this.data.info.realtime_models),
                    this._modelField("backend_model", this.data.info.backend_models),
                  ],
              errors,
            )}
          </ha-expansion-panel>
        </div>
        <div class="card-actions">
          ${this._selected !== "new"
            ? html`<ha-button
                variant="danger"
                appearance=${this._confirmDelete ? "filled" : "plain"}
                @click=${this._delete}
                >${this.localize(this._confirmDelete ? "common.delete_confirm" : "common.delete")}</ha-button
              >`
            : nothing}
          <span class="spacer"></span>
          ${dirty
            ? html`<ha-button appearance="plain" @click=${this._discard}
                >${this.localize("common.cancel")}</ha-button
              >`
            : nothing}
          <ha-button
            appearance="filled"
            .disabled=${!dirty || this._saving}
            .loading=${this._saving}
            @click=${this._save}
            >${this.localize("common.save")}</ha-button
          >
        </div>
      </ha-card>
    `;
  }

  private _modelField(name: string, options: string[]): FormSchema {
    return {
      name,
      required: true,
      selector: { select: { options, custom_value: true, mode: "dropdown" } },
    };
  }

  private _form(schema: FormSchema[], errors: Record<string, string>): TemplateResult {
    return html`<ha-form
      .hass=${this.hass}
      .data=${this._draft}
      .schema=${schema}
      .error=${errors}
      .computeLabel=${(item: FormSchema) =>
        item.name === "llm_hass_api"
          ? this.localize("assistants.llm_apis")
          : this.localize(`assistants.fields.${item.name}`)}
      .computeHelper=${(item: FormSchema) => {
        if (item.name === "llm_hass_api") return this.localize("assistants.llm_apis_desc");
        const key = `assistants.helpers.${item.name}`;
        const text = this.localize(key);
        return text === key ? undefined : text;
      }}
      @value-changed=${(ev: CustomEvent) => this._update(ev.detail.value)}
    ></ha-form>`;
  }

  private _switch(name: Toggle, icon: string): TemplateResult {
    return html`
      <div class="switch-row">
        <ha-icon .icon=${icon}></ha-icon>
        <div class="text">
          <div class="heading">${this.localize(`assistants.${name}`)}</div>
          <div class="description">${this.localize(`assistants.${name}_desc`)}</div>
        </div>
        <ha-switch
          .checked=${this._draft![name]}
          @change=${(ev: Event) =>
            this._update({ [name]: (ev.target as HTMLInputElement).checked } as Partial<Assistant>)}
        ></ha-switch>
      </div>
    `;
  }

  private _select(assistant: Assistant): void {
    this._selected = assistant.id ?? null;
    this._draft = structuredClone(assistant);
    this._errors = {};
    this._confirmDelete = false;
  }

  private _new(): void {
    const info = this.data.info;
    this._selected = "new";
    this._draft = {
      name: "",
      code: nextFreeCode(this.data, 0),
      engine: "live",
      voice: info.voices[0] ?? "marin",
      prompt: "",
      home_control: false,
      llm_hass_api: info.llm_apis.some((api) => api.id === "assist") ? ["assist"] : [],
      phone_commands: false,
      web_search: false,
      fast_interrupt: true,
      announce: true,
      live_model: info.live_models[0],
      backend_model: info.backend_models[0],
      reasoning_effort: "low",
      realtime_model: info.realtime_models[0],
    };
    this._errors = {};
    this._confirmDelete = false;
  }

  private _close(): void {
    this._selected = null;
    this._draft = null;
  }

  private _discard(): void {
    const original = this._original;
    if (original) {
      this._select(original);
    } else {
      this._close();
    }
  }

  private _update(changes: Partial<Assistant>): void {
    if (this._draft === null) return;
    this._draft = { ...this._draft, ...changes };
    this._confirmDelete = false;
  }

  private async _save(): Promise<void> {
    if (this._draft === null) return;
    this._saving = true;
    try {
      const result = await saveItem(this.hass, this.data.entry_id, "assistant", this._draft);
      if (result.errors) {
        this._errors = result.errors;
        showToast(this, this.localize("common.form_errors"));
        return;
      }
      this._errors = {};
      const config = result.config!;
      const saved =
        config.assistants.find((assistant) => assistant.id === this._draft!.id) ??
        config.assistants.find((assistant) => assistant.code === this._draft!.code.toUpperCase());
      fireConfigChanged(this, config);
      if (saved) {
        this._selected = saved.id ?? null;
        this._draft = structuredClone(saved);
      }
      showToast(this, this.localize("common.saved"));
    } catch (err: any) {
      showToast(this, this.localize("common.save_failed", { error: err?.message ?? String(err) }));
    } finally {
      this._saving = false;
    }
  }

  private async _delete(): Promise<void> {
    if (!this._confirmDelete) {
      this._confirmDelete = true;
      return;
    }
    if (!this._selected || this._selected === "new") return;
    const result = await deleteItem(this.hass, this.data.entry_id, "assistant", this._selected);
    if (result.config) fireConfigChanged(this, result.config);
    this._close();
    this._confirmDelete = false;
  }
}

if (!customElements.get("sip-assistant-assistants")) {
  customElements.define("sip-assistant-assistants", SipAssistantsView);
}
