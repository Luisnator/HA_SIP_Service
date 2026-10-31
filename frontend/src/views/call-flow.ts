import { LitElement, html, type PropertyValues, type TemplateResult } from "lit";

import { saveSection, showToast } from "../api";
import type { Localize } from "../localize";
import { sharedStyles } from "../styles";
import type { CallOptions, FormSchema, HomeAssistant, PanelData } from "../types";
import { fireConfigChanged, isDirty, translateErrors } from "./helpers";

const DEFAULTS: CallOptions = {
  start: "menu",
  greeting: "",
  announce_menu: true,
  menu_prompt: "",
  pin: "",
  tts_engine: "",
  language: "",
  digit_timeout: 3,
  max_call_duration: 15,
};

export class SipCallFlowView extends LitElement {
  static properties = {
    hass: { attribute: false },
    data: { attribute: false },
    localize: { attribute: false },
    narrow: { type: Boolean },
    _draft: { state: true },
    _errors: { state: true },
    _saving: { state: true },
  };

  static styles = sharedStyles;

  declare hass: HomeAssistant;
  declare data: PanelData;
  declare localize: Localize;
  declare narrow: boolean;
  declare _draft: CallOptions;
  declare _errors: Record<string, string>;
  declare _saving: boolean;

  constructor() {
    super();
    this.narrow = false;
    this._draft = { ...DEFAULTS };
    this._errors = {};
    this._saving = false;
  }

  private get _original(): CallOptions {
    return { ...DEFAULTS, ...this.data.call };
  }

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("data") && (!changed.get("data") || !isDirty(this._draft, changed.get("data")?.call))) {
      this._draft = this._original;
    }
  }

  private _schema(): FormSchema[] {
    return [
      {
        name: "start",
        required: true,
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "menu", label: this.localize("call.start_menu") },
              ...this.data.assistants.map((assistant) => ({
                value: assistant.id,
                label: `${assistant.name} (${assistant.code})`,
              })),
            ],
          },
        },
      },
      { name: "greeting", selector: { template: {} } },
      { name: "announce_menu", selector: { boolean: {} } },
      { name: "menu_prompt", selector: { template: {} } },
      { name: "pin", selector: { text: { type: "password", autocomplete: "off" } } },
      { name: "tts_engine", selector: { entity: { filter: { domain: "tts" } } } },
      { name: "language", selector: { language: {} } },
      {
        name: "digit_timeout",
        required: true,
        selector: {
          number: { min: 1, max: 10, step: 0.5, mode: "slider", unit_of_measurement: "s" },
        },
      },
      {
        name: "max_call_duration",
        required: true,
        selector: { number: { min: 1, max: 120, step: 1, mode: "box", unit_of_measurement: "min" } },
      },
    ];
  }

  protected render(): TemplateResult {
    const dirty = isDirty(this._draft, this._original);
    return html`
      <ha-card>
        <div class="card-header">${this.localize("call.title")}</div>
        <div class="card-subtitle">${this.localize("call.description")}</div>
        <div class="card-content">
          <ha-form
            .hass=${this.hass}
            .data=${this._draft}
            .schema=${this._schema()}
            .error=${translateErrors(this._errors, this.localize)}
            .computeLabel=${(schema: FormSchema) => this.localize(`call.fields.${schema.name}`)}
            .computeHelper=${(schema: FormSchema) => {
              const key = `call.helpers.${schema.name}`;
              const text = this.localize(key);
              return text === key ? undefined : text;
            }}
            @value-changed=${(ev: CustomEvent) => {
              this._draft = { ...this._draft, ...ev.detail.value };
            }}
          ></ha-form>
        </div>
        <div class="card-actions">
          ${dirty
            ? html`<ha-button appearance="plain" @click=${() => (this._draft = this._original)}
                >${this.localize("common.cancel")}</ha-button
              >`
            : ""}
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

  private async _save(): Promise<void> {
    this._saving = true;
    try {
      const result = await saveSection(this.hass, this.data.entry_id, "call", { ...this._draft });
      if (result.errors) {
        this._errors = result.errors;
        showToast(this, this.localize("common.form_errors"));
        return;
      }
      this._errors = {};
      this._draft = { ...DEFAULTS, ...result.config!.call };
      fireConfigChanged(this, result.config!);
      showToast(this, this.localize("common.saved"));
    } catch (err: any) {
      showToast(this, this.localize("common.save_failed", { error: err?.message ?? String(err) }));
    } finally {
      this._saving = false;
    }
  }
}

if (!customElements.get("sip-assistant-call-flow")) {
  customElements.define("sip-assistant-call-flow", SipCallFlowView);
}
