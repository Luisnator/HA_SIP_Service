/** Minimal typing of the Home Assistant frontend objects the panel uses. */

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
  last_changed: string;
}

export interface HomeAssistant {
  language: string;
  locale?: { language: string };
  states: Record<string, HassEntity>;
  user?: { is_admin: boolean; name: string };
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  callService(domain: string, service: string, data?: Record<string, unknown>): Promise<unknown>;
}

export interface PanelInfo {
  url_path: string;
  title: string | null;
}

export interface Route {
  prefix: string;
  path: string;
}

export type ActionType = "entity" | "actions" | "announcement";
export type Engine = "live" | "realtime";

export interface Command {
  id?: string;
  name: string;
  code: string;
  action_type: ActionType;
  entity_id?: string;
  actions?: unknown[];
  response?: string;
  announce: boolean;
  ai_enabled: boolean;
  description?: string;
}

export interface Assistant {
  id?: string;
  name: string;
  code: string;
  engine: Engine;
  voice: string;
  prompt?: string;
  home_control: boolean;
  llm_hass_api: string[];
  phone_commands: boolean;
  web_search: boolean;
  fast_interrupt: boolean;
  announce: boolean;
  live_model: string;
  backend_model: string;
  reasoning_effort: string;
  realtime_model: string;
}

export interface CallOptions {
  start: string;
  greeting?: string;
  announce_menu: boolean;
  menu_prompt?: string;
  pin?: string;
  tts_engine?: string;
  language?: string;
  digit_timeout: number;
  max_call_duration: number;
}

export interface NetworkOptions {
  allowed_networks: string;
  rtp_port_start: number;
  rtp_port_end: number;
  external_host?: string;
  max_calls: number;
}

export interface ConnectionInfo {
  sip_port: number;
  sip_user: string;
  has_sip_password: boolean;
  has_api_key: boolean;
  api_key_hint: string;
}

export interface PanelData {
  entries: { entry_id: string; title: string }[];
  entry_id: string;
  title: string;
  loaded: boolean;
  connection: ConnectionInfo;
  call: CallOptions;
  network: NetworkOptions;
  commands: Command[];
  assistants: Assistant[];
  info: {
    version: string;
    language: string;
    sip_uri: string | null;
    tts_engine: string | null;
    voip_loaded: boolean;
    llm_apis: { id: string; name: string }[];
    entity_domains: string[];
    voices: string[];
    live_models: string[];
    backend_models: string[];
    realtime_models: string[];
    reasoning_efforts: string[];
    entities: Record<string, string | null>;
  };
}

export interface SaveResult {
  config?: PanelData;
  errors?: Record<string, string>;
}

/** ha-form schema entry. */
export type FormSchema = Record<string, any>;
