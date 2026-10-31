import { LitElement, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { saveSection, showToast, type Section } from "../api";
import type { Localize } from "../localize";
import { sharedStyles } from "../styles";
import type { FormSchema, HomeAssistant, NetworkOptions, PanelData } from "../types";
import { fireConfigChanged, isDirty, translateErrors } from "./helpers";

interface SipDraft {
  sip_port: number;
  sip_user: string;
  sip_password: string;
  clear_sip_password: boolean;
}

interface KeyDraft {
  api_key: string;
  clear_api_key: boolean;
}

const NETWORK_DEFAULTS: NetworkOptions = {
  allowed_networks: "",
  rtp_port_start: 10000,
  rtp_port_end: 10100,
  external_host: "",
  max_calls: 2,
};

export class SipConnectionView extends LitElement {
  static properties = {
    hass: { attribute: false },
    data: { attribute: false },
    localize: { attribute: false },
    narrow: { type: Boolean },
    _sip: { state: true },
    _key: { state: true },
    _network: { state: true },
    _errors: { state: true },
    _saving: { state: true },
  };

  static styles = sharedStyles;

  declare hass: HomeAssistant;
  declare data: PanelData;
  declare localize: Localize;
  declare narrow: boolean;
  declare _sip: SipDraft;
  declare _key: KeyDraft;
  declare _network: NetworkOptions;
  declare _errors: Record<string, string>;
  declare _saving: string | null;

  constructor() {
    super();
    this.narrow = false;
    this._errors = {};
    this._saving = null;
  }

  private get _sipOriginal(): SipDraft {
    return {
      sip_port: this.data.connection.sip_port,
      sip_user: this.data.connection.sip_user,
      sip_password: "",
      clear_sip_password: false,
    };
  }

  private get _networkOriginal(): NetworkOptions {
    return { ...NETWORK_DEFAULTS, ...this.data.network };
  }

  protected willUpdate(changed: PropertyValues): void {
    if (changed.has("data")) {
      this._sip = this._sipOriginal;
      this._key = { api_key: "", clear_api_key: false };
      this._network = this._networkOriginal;
    }
  }

  protected render(): TemplateResult {
    const connection = this.data.connection;
    const errors = translateErrors(this._errors, this.localize);
    const sipDirty = isDirty(this._sip, this._sipOriginal);
    const keyDirty = this._key.api_key !== "" || this._key.clear_api_key;
    const networkDirty = isDirty(this._network, this._networkOriginal);
    return html`
      <ha-card>
        <div class="card-header">${this.localize("connection.sip")}</div>
        <div class="card-subtitle">${this.localize("connection.sip_desc")}</div>
        <div class="card-content">
          ${this._form(
            this._sip,
            [
              {
                    name: "sip_port",
                    required: true,
                    selector: { number: { min: 1, max: 65535, mode: "box" } },
                  },
                  { name: "sip_user", required: true, selector: { text: {} } },
              {
                name: "sip_password",
                selector: { text: { type: "password", autocomplete: "new-password" } },
              },
              ...(connection.has_sip_password
                ? [{ name: "clear_sip_password", selector: { boolean: {} } }]
                : []),
            ],
            errors,
            (value) => (this._sip = { ...this._sip, ...value }),
            (name) =>
              name === "sip_password"
                ? this.localize(
                    connection.has_sip_password
                      ? "connection.helpers.password_set"
                      : "connection.helpers.password_none",
                  )
                : undefined,
          )}
        </div>
        ${this._actions("sip", sipDirty, () => (this._sip = this._sipOriginal))}
      </ha-card>

      <ha-card>
        <div class="card-header">${this.localize("connection.openai")}</div>
        <div class="card-subtitle">${this.localize("connection.openai_desc")}</div>
        <div class="card-content">
          ${!connection.has_api_key
            ? html`<ha-alert alert-type="info">${this.localize("connection.helpers.api_key_link")}</ha-alert>`
            : nothing}
          ${this._form(
            this._key,
            [
              {
                name: "api_key",
                selector: { text: { type: "password", autocomplete: "off" } },
              },
              ...(connection.has_api_key ? [{ name: "clear_api_key", selector: { boolean: {} } }] : []),
            ],
            errors,
            (value) => (this._key = { ...this._key, ...value }),
            (name) =>
              name === "api_key"
                ? connection.has_api_key
                  ? this.localize("connection.helpers.api_key_set", { hint: connection.api_key_hint })
                  : this.localize("connection.helpers.api_key_none")
                : undefined,
          )}
        </div>
        ${this._actions("key", keyDirty, () => (this._key = { api_key: "", clear_api_key: false }))}
      </ha-card>

      <ha-card>
        <div class="card-header">${this.localize("connection.network")}</div>
        <div class="card-subtitle">${this.localize("connection.network_desc")}</div>
        <div class="card-content">
          ${this._form(
            this._network,
            [
              { name: "allowed_networks", selector: { text: {} } },
              {
                    name: "rtp_port_start",
                    required: true,
                    selector: { number: { min: 1024, max: 65535, mode: "box" } },
                  },
                  {
                    name: "rtp_port_end",
                    required: true,
                    selector: { number: { min: 1024, max: 65535, mode: "box" } },
                  },
              { name: "external_host", selector: { text: {} } },
              {
                name: "max_calls",
                required: true,
                selector: { number: { min: 1, max: 10, mode: "box" } },
              },
            ],
            errors,
            (value) => (this._network = { ...this._network, ...value }),
            (name) => {
              const key = `connection.helpers.${name}`;
              const text = this.localize(key);
              return text === key ? undefined : text;
            },
          )}
        </div>
        ${this._actions("network", networkDirty, () => (this._network = this._networkOriginal))}
      </ha-card>
    `;
  }

  private _form(
    data: object,
    schema: FormSchema[],
    errors: Record<string, string>,
    onChange: (value: any) => void,
    helper: (name: string) => string | undefined,
  ): TemplateResult {
    return html`<ha-form
      .hass=${this.hass}
      .data=${data}
      .schema=${schema}
      .error=${errors}
      .computeLabel=${(item: FormSchema) => this.localize(`connection.fields.${item.name}`)}
      .computeHelper=${(item: FormSchema) => helper(item.name)}
      @value-changed=${(ev: CustomEvent) => onChange(ev.detail.value)}
    ></ha-form>`;
  }

  private _actions(card: string, dirty: boolean, discard: () => void): TemplateResult {
    return html`
      <div class="card-actions">
        ${dirty
          ? html`<ha-button appearance="plain" @click=${discard}>${this.localize("common.cancel")}</ha-button>`
          : nothing}
        <ha-button
          appearance="filled"
          .disabled=${!dirty || this._saving !== null}
          .loading=${this._saving === card}
          @click=${() => this._save(card)}
          >${this.localize("common.save")}</ha-button
        >
      </div>
    `;
  }

  private async _save(card: string): Promise<void> {
    let section: Section = "connection";
    let values: Record<string, unknown>;
    if (card === "network") {
      section = "network";
      values = { ...this._network };
    } else {
      values = { sip_port: this._sip.sip_port, sip_user: this._sip.sip_user };
      if (card === "sip") {
        if (this._sip.clear_sip_password) values.sip_password = "";
        else if (this._sip.sip_password) values.sip_password = this._sip.sip_password;
      } else {
        values.sip_port = this.data.connection.sip_port;
        values.sip_user = this.data.connection.sip_user;
        if (this._key.clear_api_key) values.api_key = "";
        else if (this._key.api_key) values.api_key = this._key.api_key;
      }
    }
    this._saving = card;
    try {
      const result = await saveSection(this.hass, this.data.entry_id, section, values);
      if (result.errors) {
        this._errors = result.errors;
        showToast(this, this.localize("common.form_errors"));
        return;
      }
      this._errors = {};
      fireConfigChanged(this, result.config!);
      showToast(this, this.localize("common.saved"));
    } catch (err: any) {
      showToast(this, this.localize("common.save_failed", { error: err?.message ?? String(err) }));
    } finally {
      this._saving = null;
    }
  }
}

if (!customElements.get("sip-assistant-connection")) {
  customElements.define("sip-assistant-connection", SipConnectionView);
}
