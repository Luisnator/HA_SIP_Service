"""Read the colour state of lights for the voice assistants.

Home Assistant's GetLiveContext tool only reports the state and brightness of
lights, so the assistants cannot answer "what colour is the light" or change a
colour relative to the current one. This tool adds that information for the
lights exposed to Assist.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.homeassistant.llm import async_get_exposed_entities
from homeassistant.core import HomeAssistant
from homeassistant.util.color import COLORS

LIGHT_DOMAIN = "light"


def closest_color_name(rgb: tuple[int, int, int] | list[int]) -> str:
    """Return the name of the named colour closest to an RGB value."""
    red, green, blue = rgb
    return min(
        COLORS,
        key=lambda name: (
            (COLORS[name].r - red) ** 2
            + (COLORS[name].g - green) ** 2
            + (COLORS[name].b - blue) ** 2
        ),
    )


def _matches(text: str | None, value: str) -> bool:
    return bool(text) and value.casefold() in text.casefold()


def light_details(
    hass: HomeAssistant, assistant: str, name: str | None = None, area: str | None = None
) -> list[dict[str, Any]]:
    """Describe the exposed lights, optionally filtered by name or area."""
    lights: list[dict[str, Any]] = []
    exposed = async_get_exposed_entities(hass, assistant, include_state=False)
    for entity_id, info in exposed.items():
        if info["domain"] != LIGHT_DOMAIN or (state := hass.states.get(entity_id)) is None:
            continue
        if name and not (_matches(info.get("names"), name) or _matches(entity_id, name)):
            continue
        if area and not _matches(info.get("areas"), area):
            continue
        attributes = state.attributes
        details: dict[str, Any] = {
            "name": info["names"].split(", ")[0],
            "state": state.state,
        }
        if areas := info.get("areas"):
            details["area"] = areas.split(", ")[0]
        if (brightness := attributes.get("brightness")) is not None:
            details["brightness_pct"] = round(brightness / 255 * 100)
        if color_mode := attributes.get("color_mode"):
            details["color_mode"] = str(color_mode)
        if (rgb := attributes.get("rgb_color")) is not None:
            details["rgb_color"] = list(rgb)
            details["color_name"] = closest_color_name(rgb)
        if (kelvin := attributes.get("color_temp_kelvin")) is not None:
            details["color_temp_kelvin"] = kelvin
        if modes := attributes.get("supported_color_modes"):
            details["supported_color_modes"] = sorted(str(mode) for mode in modes)
        if (minimum := attributes.get("min_color_temp_kelvin")) is not None:
            details["min_color_temp_kelvin"] = minimum
        if (maximum := attributes.get("max_color_temp_kelvin")) is not None:
            details["max_color_temp_kelvin"] = maximum
        lights.append(details)
    return lights
