import type { Localize } from "../localize";
import type { PanelData } from "../types";

export const translateErrors = (
  errors: Record<string, string>,
  localize: Localize,
): Record<string, string> =>
  Object.fromEntries(
    Object.entries(errors).map(([field, key]) => [field, localize(`errors.${key}`)]),
  );

/** Tell the panel that the server returned a new configuration. */
export const fireConfigChanged = (element: HTMLElement, config: PanelData): void => {
  element.dispatchEvent(
    new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }),
  );
};

export const fireNavigate = (element: HTMLElement, tab: string): void => {
  element.dispatchEvent(
    new CustomEvent("navigate-tab", { detail: { tab }, bubbles: true, composed: true }),
  );
};

export const byCode = <T extends { code: string }>(items: T[]): T[] =>
  [...items].sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }));

/** Suggest the lowest single digit that is not used yet. */
export const nextFreeCode = (data: PanelData, preferred = 1): string => {
  const used = new Set([...data.commands, ...data.assistants].map((item) => item.code));
  for (let offset = 0; offset < 10; offset++) {
    const code = String((preferred + offset) % 10);
    if (!used.has(code)) return code;
  }
  for (let code = 10; code < 100; code++) {
    if (!used.has(String(code))) return String(code);
  }
  return "";
};

/** Serialize with sorted keys and without empty values so key order and unset
 * optional fields do not count as changes. */
const normalize = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([, item]) => item !== undefined && item !== null && item !== "")
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, normalize(item)]),
    );
  }
  return value;
};

export const isDirty = (draft: unknown, original: unknown): boolean =>
  original === undefined || JSON.stringify(normalize(draft)) !== JSON.stringify(normalize(original));
