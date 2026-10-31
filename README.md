# SIP Assistant for Home Assistant

Call your home: this integration turns Home Assistant into a SIP endpoint. Use the
**keypad (DTMF)** to run scripts, automations and scenes, and talk to **voice assistants**
(OpenAI GPT-Live or the Realtime API) that control your home through Home Assistant's
Assist tools, all configured in a dedicated sidebar panel.

- 📞 Built-in SIP server (UDP) for direct calls by IP from softphones, SIP desk phones or
  analog telephone adapters
- 🔢 Keypad commands: run a script, automation, scene or button, toggle an entity, run
  custom actions or speak a template (e.g. a sensor value)
- 🗣️ Multiple voice assistants, each on its own key, with its own model, voice,
  instructions and permissions (device control, keypad commands, web search)
- ⚡ Fast interruption: the assistant stops as soon as the caller talks over it
- 🖥️ Configuration panel in the sidebar built from Home Assistant's own components
  (entity picker, action editor, template editor), with live status and setup checks
- 🔐 PIN, SIP digest authentication, network allow list and a maximum call duration
- 📊 Entities for call state, last caller, call events and a hang-up button
- 🌍 English and German, announcements through the text-to-speech engine of your choice
  (tones as a fallback)

## Requirements

- Home Assistant **2026.10** or newer (OS, Supervised, Container or Core)
- A text-to-speech engine for announcements (e.g. Piper, Google Translate, Home Assistant
  Cloud). Without one, tones are played instead.
- An OpenAI API key for the voice assistants (<https://platform.openai.com/api-keys>)
- Network: the SIP port (UDP, default 5060) and a UDP port range for audio (default
  10000–10100) must be reachable on the Home Assistant host. With **Docker**, run the
  container with `network_mode: host`.

> The built-in **Voice over IP** integration also uses port 5060 by default. If you use it,
> pick another port for SIP Assistant (e.g. 5070). The setup detects ports that are in use.

## Installation

### HACS (recommended)

1. HACS → ⋮ → *Custom repositories* → `https://github.com/Luisnator/HA_SIP_Service`,
   type *Integration*.
2. Install **SIP Assistant** and restart Home Assistant.

### Manual

Copy `custom_components/sip_assistant` to `<config>/custom_components/` and restart
Home Assistant.

## Setup

**Settings → Devices & services → Add integration → SIP Assistant**

1. **Phone connection**: port, SIP user (e.g. `homeassistant`) and an optional password.
   With a password, phones have to authenticate with digest authentication.
2. **Voice assistant**: optionally enter the OpenAI API key and pick the default model. You
   can add or change the key later in the panel.

A default assistant on key `0` with access to your home is created. Everything else is
configured in the **SIP Assistant** panel in the sidebar (admins only). The *Configure*
button on the integration page opens it as well.

## The configuration panel

| Tab | What you can do |
| --- | --- |
| **Overview** | Live call state, the SIP address to dial (with copy button), last caller, a hang-up button, the complete keypad layout and checks such as a missing API key, missing TTS or risky assistant settings |
| **Keypad commands** | Create commands with a code, pick what they do, set a spoken confirmation and decide whether they are announced and whether assistants may run them |
| **Assistants** | Create voice assistant profiles, each with its own key, model, voice, instructions and permissions |
| **Call flow** | Start with the keypad menu or directly with an assistant, greeting, menu announcement, PIN, TTS engine, language, digit timeout and maximum call duration |
| **Connection** | SIP port, user and password, OpenAI API key, allowed networks, RTP port range, advertised address and number of simultaneous calls |

Changes to commands, assistants and the call flow apply to the next call without
interrupting running calls. Changing the SIP connection or network settings restarts the
SIP server.

### Keypad commands

| Type | Description |
| --- | --- |
| Run an entity | Start a script or scene, trigger an automation, press a button or toggle a light, switch, fan, cover or input boolean |
| Custom actions | Any sequence built with the action editor. The variables `caller`, `caller_name` and `code` are available |
| Speak a text | Read out a template, e.g. `It is {{ states('sensor.outdoor_temperature') }} degrees outside.` |

Codes are 1–8 characters from `0–9` and `A–D`; `*` and `#` are reserved.

### Assistant profiles

Every assistant answers on its own key, so you can offer different assistants for
different purposes, for example:

| Key | Assistant | Device control | Keypad commands | Web search |
| --- | --- | --- | --- | --- |
| `0` | Home | ✅ | ✅ | ❌ |
| `1` | Research | ❌ | ❌ | ✅ |

Per profile you choose:

- **Model**: *GPT-Live* (full-duplex voice model that hands tool use to a fast backend
  model) or the *Realtime API* (one speech-to-speech model that uses the tools itself)
- **Voice** and **instructions** (templates with `caller` and `caller_name` are supported)
- **Control devices** through the selected Home Assistant APIs (*Assist* only sees
  entities exposed to Assist)
- **Run keypad commands** that allow it
- **Web search** for current information. GPT-Live uses OpenAI's hosted web search in its
  backend; the Realtime API calls a web search function that uses the Responses API.
- **Fast interruption** (on by default): the integration detects the caller talking over
  the assistant on the phone line and stops playback immediately instead of waiting for
  OpenAI's turn detection. Turn it off if background noise cuts the assistant off.

If a profile combines web search with device control or keypad commands, the panel shows a
warning: web pages can contain hidden instructions (prompt injection) that try to make the
assistant act in your home.

## Using the phone

1. Greeting, then the PIN if one is set (finish with `#`)
2. Menu announcement; any key interrupts it
3. Enter a code: unique codes run immediately, otherwise after the digit timeout or `#`
4. `*` repeats the menu; an assistant's key connects you to that assistant
5. During a conversation, `*` returns to the menu; saying goodbye ends the call

### Softphone setup

- **Linphone, MicroSIP**: dial `sip:homeassistant@<home-assistant-ip>` without an account
  (append `:5070` etc. for another port).
- **With a password, or apps that require an account (e.g. Zoiper)**: create a SIP account
  with the SIP user as username and `<home-assistant-ip>:<port>` as domain/server over UDP.
  SIP Assistant accepts the registration; then call the SIP user.
- **Codecs and DTMF**: G.711 A-law (PCMA) and µ-law (PCMU); DTMF via RFC 4733 ("RFC 2833")
  or SIP INFO. SRTP is not supported; use a VPN for calls from outside your network.

## Automations

Every event is shown on the **Call** event entity (`event.sip_assistant_call`) and fired on
the event bus as `sip_assistant_<type>`:

| Event | Data |
| --- | --- |
| `call_started`, `call_ended` | `caller`, `caller_name`, `caller_address`, `call_id`; on end also `reason` and `duration` |
| `code_entered` | `code`, `command` (`null` for unknown codes) |
| `command_executed` | `code`, `command`, `success` |
| `assistant_started` | caller data, `assistant`, `assistant_id` |
| `pin_failed`, `call_rejected` | caller data or `reason` |

Example: react to a code that has no keypad command:

```yaml
triggers:
  - trigger: event
    event_type: sip_assistant_code_entered
    event_data:
      code: "4711"
actions:
  - action: lock.unlock
    target:
      entity_id: lock.front_door
```

## Security and privacy

- By default only private networks may call. Do **not** forward the SIP port to the
  internet without protection.
- Set a SIP password and/or a PIN, especially when commands control doors or alarms.
- Assistants only see entities exposed to Assist
  (*Settings → Voice assistants → Expose*), and only when *Control devices* is enabled.
- Audio is sent to OpenAI only while an assistant is active, never in the keypad menu.
- The maximum call duration ends every call after the configured time.

## Troubleshooting

```yaml
logger:
  logs:
    custom_components.sip_assistant: debug
```

- **No audio or one-way audio**: open the RTP port range in your firewall; use
  `network_mode: host` with Docker; set the advertised address behind NAT.
- **Keys are not recognised**: set the softphone's DTMF mode to "RFC 2833/4733" or
  "SIP INFO" (in-band DTMF is not evaluated).
- **The assistant cuts itself off**: turn off *Fast interruption* for that assistant.
- **Setup fails because the port is in use**: choose another SIP port, e.g. when the Voice
  over IP integration is active.
- The diagnostics download (integration page → ⋮ → Download diagnostics) contains the
  settings without passwords or keys, and the active calls.

## Development

Backend:

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest tests
.venv/bin/ruff check custom_components tests
```

Panel (TypeScript and Lit, bundled into
`custom_components/sip_assistant/frontend/sip-assistant-panel.js`, which is committed so
HACS installs work without a build step):

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

| Path | Contents |
| --- | --- |
| `custom_components/sip_assistant/sip/` | SIP parser, SDP, digest authentication and the UDP server (transactions, dialogs, registrar) |
| `custom_components/sip_assistant/rtp/` | RTP packets, paced audio session, G.711, DTMF (RFC 4733 and INFO), tones |
| `custom_components/sip_assistant/call_session.py` | What happens during a call: greeting, PIN, keypad menu, assistants |
| `custom_components/sip_assistant/voice/` | GPT-Live and Realtime agents, Home Assistant tool bridge, web search, fast interruption |
| `custom_components/sip_assistant/websocket.py`, `panel.py` | Panel registration and its admin-only websocket API |
| `custom_components/sip_assistant/validation.py`, `defaults.py` | Validation shared by the config flow and the panel, defaults and migration |
| `frontend/` | Source of the configuration panel |
