import { LitElement, html, nothing, type TemplateResult } from "lit";

import { deleteItem, saveItem, showToast } from "../api";
import type { Localize } from "../localize";
import { sharedStyles } from "../styles";
import type { ActionType, Command, FormSchema, HomeAssistant, PanelData } from "../types";
import {
  byCode,
  fireConfigChanged,
  isDirty,
  nextFreeCode,
  translateErrors,
} from "./helpers";

const TYPES: { type: ActionType; icon: string }[] = [
  { type: "entity", icon: "mdi:play-circle-outline" },
  { type: "actions", icon: "mdi:format-list-bulleted-square" },
  { type: "announcement", icon: "mdi:account-voice" },
];

export class SipCommandsView extends LitElement {
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
  declare _draft: Command | null;
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

  private get _original(): Command | undefined {
    return this.data.commands.find((command) => command.id === this._selected);
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

  private _renderList(): TemplateResult {
    const commands = byCode(this.data.commands);
    return html`
      <ha-card>
        <div class="card-header">
          <span>${this.localize("tabs.commands")}</span>
          <ha-button appearance="filled" size="small" @click=${this._new}>
            <ha-icon slot="start" icon="mdi:plus"></ha-icon>
            ${this.localize("commands.add")}
          </ha-button>
        </div>
        <div class="list">
          ${commands.length === 0
            ? html`<div class="empty">${this.localize("commands.empty")}</div>`
            : commands.map(
                (command) => html`
                  <button
                    class="list-item ${command.id === this._selected ? "selected" : ""}"
                    @click=${() => this._select(command)}
                  >
                    <span class="code">${command.code}</span>
                    <span class="text">
                      <div class="primary">${command.name}</div>
                      <div class="secondary">${this._describe(command)}</div>
                      <div class="badges">
                        ${command.announce
                          ? html`<span class="badge"
                              ><ha-icon icon="mdi:bullhorn-outline"></ha-icon>${this.localize(
                                "commands.badge_menu",
                              )}</span
                            >`
                          : nothing}
                        ${command.ai_enabled
                          ? html`<span class="badge accent"
                              ><ha-icon icon="mdi:robot-outline"></ha-icon>${this.localize(
                                "commands.badge_ai",
                              )}</span
                            >`
                          : nothing}
                      </div>
                    </span>
                  </button>
                `,
              )}
        </div>
      </ha-card>
    `;
  }

  private _describe(command: Command): string {
    switch (command.action_type) {
      case "entity": {
        const state = command.entity_id ? this.hass.states[command.entity_id] : undefined;
        return state?.attributes.friendly_name ?? command.entity_id ?? "";
      }
      case "actions":
        return `${this.localize("commands.type_actions")} (${command.actions?.length ?? 0})`;
      default:
        return command.response ?? "";
    }
  }

  private _renderEditor(): TemplateResult {
    if (this._draft === null) {
      return html`
        <ha-card>
          <div class="placeholder">
            <ha-icon icon="mdi:dialpad"></ha-icon>
            <div>${this.localize("commands.select")}</div>
          </div>
        </ha-card>
      `;
    }
    const draft = this._draft;
    const dirty = isDirty(draft, this._original);
    return html`
      <ha-card>
        <div class="editor-header">
          ${this.narrow
            ? html`<button class="icon-button" @click=${this._close} title=${this.localize("common.back")}>
                <ha-icon icon="mdi:arrow-left"></ha-icon>
              </button>`
            : nothing}
          <span class="code">${draft.code || "?"}</span>
          <span class="title">${draft.name || this.localize("commands.new")}</span>
        </div>
        <div class="card-content">
          <div class="section-title">${this.localize("commands.type")}</div>
          <div class="tiles">
            ${TYPES.map(
              ({ type, icon }) => html`
                <button
                  class="tile ${draft.action_type === type ? "selected" : ""}"
                  @click=${() => this._update({ action_type: type })}
                >
                  <span class="tile-title"><ha-icon .icon=${icon}></ha-icon>${this.localize(
                    `commands.type_${type}`,
                  )}</span>
                  <span class="tile-desc">${this.localize(`commands.type_${type}_desc`)}</span>
                </button>
              `,
            )}
          </div>
          <ha-form
            .hass=${this.hass}
            .data=${draft}
            .schema=${this._schema(draft.action_type)}
            .error=${translateErrors(this._errors, this.localize)}
            .computeLabel=${(schema: FormSchema) => this._label(schema, draft.action_type)}
            .computeHelper=${(schema: FormSchema) => this._helper(schema, draft.action_type)}
            @value-changed=${(ev: CustomEvent) => this._update(ev.detail.value)}
          ></ha-form>
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

  private _schema(type: ActionType): FormSchema[] {
    const schema: FormSchema[] = [
      { name: "name", required: true, selector: { text: {} } },
          { name: "code", required: true, selector: { text: {} } },
    ];
    if (type === "entity") {
      schema.push({
        name: "entity_id",
        required: true,
        selector: { entity: { filter: { domain: this.data.info.entity_domains } } },
      });
    }
    if (type === "actions") {
      schema.push({ name: "actions", required: true, selector: { action: {} } });
    }
    schema.push(
      { name: "response", required: type === "announcement", selector: { template: {} } },
      { name: "announce", selector: { boolean: {} } },
      { name: "ai_enabled", selector: { boolean: {} } },
      { name: "description", selector: { text: {} } },
    );
    return schema;
  }

  private _label(schema: FormSchema, type: ActionType): string {
    const name = schema.name === "response" && type === "announcement" ? "response_announcement" : schema.name;
    return this.localize(`commands.fields.${name}`);
  }

  private _helper(schema: FormSchema, type: ActionType): string | undefined {
    const name = schema.name === "response" && type === "announcement" ? "response_announcement" : schema.name;
    const key = `commands.helpers.${name}`;
    const text = this.localize(key);
    return text === key ? undefined : text;
  }

  private _select(command: Command): void {
    this._selected = command.id ?? null;
    this._draft = structuredClone(command);
    this._errors = {};
    this._confirmDelete = false;
  }

  private _new(): void {
    this._selected = "new";
    this._draft = {
      name: "",
      code: nextFreeCode(this.data),
      action_type: "entity",
      entity_id: "",
      response: "",
      announce: true,
      ai_enabled: true,
      description: "",
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

  private _update(changes: Partial<Command>): void {
    if (this._draft === null) return;
    const draft = { ...this._draft, ...changes };
    if (changes.action_type === "announcement" && this._draft.action_type !== "announcement") {
      draft.ai_enabled = false;
    }
    this._draft = draft;
    this._confirmDelete = false;
  }

  private async _save(): Promise<void> {
    if (this._draft === null) return;
    this._saving = true;
    try {
      const result = await saveItem(this.hass, this.data.entry_id, "command", this._draft);
      if (result.errors) {
        this._errors = result.errors;
        showToast(this, this.localize("common.form_errors"));
        return;
      }
      this._errors = {};
      const config = result.config!;
      const saved =
        config.commands.find((command) => command.id === this._draft!.id) ??
        config.commands.find((command) => command.code === this._draft!.code.toUpperCase());
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
    const result = await deleteItem(this.hass, this.data.entry_id, "command", this._selected);
    if (result.config) fireConfigChanged(this, result.config);
    this._close();
    this._confirmDelete = false;
  }
}

if (!customElements.get("sip-assistant-commands")) {
  customElements.define("sip-assistant-commands", SipCommandsView);
}
