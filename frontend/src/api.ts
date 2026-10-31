import type { HomeAssistant, PanelData, SaveResult } from "./types";

export type ItemKind = "command" | "assistant";
export type Section = "call" | "network" | "connection";

export const fetchConfig = async (
  hass: HomeAssistant,
  entryId?: string,
): Promise<PanelData | null> =>
  (
    await hass.callWS<{ config: PanelData | null }>({
      type: "sip_assistant/config",
      ...(entryId ? { entry_id: entryId } : {}),
    })
  ).config;

export const saveSection = (
  hass: HomeAssistant,
  entryId: string,
  section: Section,
  values: Record<string, unknown>,
): Promise<SaveResult> =>
  hass.callWS<SaveResult>({
    type: "sip_assistant/save_section",
    entry_id: entryId,
    section,
    values,
  });

export const saveItem = (
  hass: HomeAssistant,
  entryId: string,
  kind: ItemKind,
  item: object,
): Promise<SaveResult> =>
  hass.callWS<SaveResult>({ type: "sip_assistant/save_item", entry_id: entryId, kind, item });

export const deleteItem = (
  hass: HomeAssistant,
  entryId: string,
  kind: ItemKind,
  id: string,
): Promise<SaveResult> =>
  hass.callWS<SaveResult>({
    type: "sip_assistant/delete_item",
    entry_id: entryId,
    kind,
    item_id: id,
  });

/** Show a toast through the Home Assistant app shell. */
export const showToast = (element: HTMLElement, message: string): void => {
  element.dispatchEvent(
    new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
  );
};

/** Navigate inside the Home Assistant app without reloading the page. */
export const navigate = (path: string, replace = false): void => {
  if (replace) {
    history.replaceState(null, "", path);
  } else {
    history.pushState(null, "", path);
  }
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
};

export const copyToClipboard = async (text: string): Promise<void> => {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
};
