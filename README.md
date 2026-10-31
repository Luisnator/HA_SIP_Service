# SIP Assistant für Home Assistant

Ruf dein Zuhause an: Diese Integration macht Home Assistant zu einem SIP-Telefon-Endpunkt.
Per **Tastenmenü (DTMF)** startest du Skripte, Automationen und Szenen, und auf Knopfdruck
sprichst du mit einem **KI-Sprachassistenten** (OpenAI GPT-Live oder Realtime-API), der
dein Haus über die Assist-Werkzeuge von Home Assistant steuert.

- 📞 Eigener SIP-Server (UDP) für Direktanrufe per IP – Softphone, SIP-Tischtelefon oder Analog-Telefonadapter
- 🔢 Tastenbefehle bequem in der UI anlegen: Skript/Automation/Szene/Button, Entität umschalten,
  eigene Aktionen oder Ansagen (z. B. Sensorwerte per Template)
- 🗣️ Sprachassistent mit OpenAI **GPT-Live** (`gpt-live-1`, vollduplex) oder der **Realtime-API**
  (`gpt-realtime-2.1` / `gpt-realtime-mini`), Audio wird verlustfrei als G.711 durchgereicht
- 🏠 Der Assistent nutzt die Assist-API (nur für Assist freigegebene Entitäten) und deine Tastenbefehle
- 🔐 PIN-Abfrage, SIP-Digest-Authentifizierung, Netzwerkfreigaben, maximale Gesprächsdauer
- 📊 Entitäten für Anrufstatus, letzten Anrufer, Anruf-Ereignisse und einen Auflegen-Button
- 🌍 Deutsch und Englisch, Ansagen über die TTS-Engine deiner Wahl (Töne als Fallback)

## Voraussetzungen

- Home Assistant **2026.10** oder neuer (HA OS, Supervised, Container oder Core)
- Für Ansagen eine TTS-Engine (z. B. Piper, Google Translate, Home Assistant Cloud) – ohne TTS
  werden Signaltöne gespielt
- Für den Sprachassistenten ein OpenAI-API-Key (<https://platform.openai.com/api-keys>)
- Netzwerk: UDP-Port für SIP (Standard 5060) und ein UDP-Portbereich für Audio (Standard
  10000–10100) müssen am Home-Assistant-Host erreichbar sein. Bei **Docker** den Container mit
  `network_mode: host` betreiben.

> Die eingebaute HA-Integration **Voice over IP** nutzt ebenfalls Port 5060. Ist sie aktiv, wähle
> hier einen anderen Port (z. B. 5070). Die Einrichtung erkennt belegte Ports.

## Installation

### HACS (empfohlen)

1. HACS → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/Luisnator/HA_SIP_Service`,
   Typ *Integration*.
2. „SIP Assistant“ installieren und Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/sip_assistant` nach `<config>/custom_components/` kopieren und
Home Assistant neu starten.

## Einrichtung

**Einstellungen → Geräte & Dienste → Integration hinzufügen → SIP Assistant**

1. **Telefonanschluss** – Port, SIP-Benutzer (z. B. `homeassistant`) und optional ein Passwort.
   Mit Passwort müssen sich Telefone per Digest-Authentifizierung anmelden.
2. **Sprachassistent** – optional den OpenAI-API-Key eintragen und das Modell wählen. Ohne Key
   funktioniert alles außer dem Sprachassistenten; der Key lässt sich später über
   *Neu konfigurieren* ergänzen.

Danach zeigt der Sensor **SIP-Adresse** die Adresse zum Anrufen, z. B. `sip:homeassistant@192.168.1.10`.

### Tastenbefehle anlegen

Auf der Integrationsseite **Tastenbefehl hinzufügen** wählen:

| Typ | Beschreibung |
| --- | --- |
| Entität ausführen | Skripte und Szenen starten, Automationen auslösen, Buttons drücken, Licht/Schalter/Lüfter/Abdeckung/Input-Boolean umschalten |
| Eigene Aktionen | Beliebige Aktionen mit dem Aktionseditor (wie in einem Skript). Variablen: `caller`, `caller_name`, `code` |
| Text ansagen | Ein Template vorlesen, z. B. `Draußen sind es {{ states('sensor.aussentemperatur') }} Grad.` |

Jeder Befehl hat einen **Code** (1–8 Zeichen aus `0–9` und `A–D`), eine optionale gesprochene
Bestätigung und zwei Schalter: *in der Menüansage nennen* und *Sprachassistent darf ihn ausführen*.

### Optionen

Unter **Konfigurieren** gibt es drei Abschnitte:

- **Anrufablauf**: Start im Tastenmenü oder direkt beim Assistenten, Begrüßung (Template),
  Menüansage (automatisch oder eigener Text), Taste für den Assistenten (Standard `0`), PIN,
  TTS-Engine, Sprache, Wartezeit für mehrstellige Codes, maximale Gesprächsdauer.
- **Sprachassistent**: Modell (GPT-Live oder Realtime), Stimme, Anweisungen (Template),
  welche Home-Assistant-APIs genutzt werden dürfen (Standard: Assist), Modelle und Denkaufwand.
- **Netzwerk und Sicherheit**: erlaubte Netzwerke (Standard: private Netze), RTP-Portbereich,
  angekündigte Adresse (nur hinter NAT nötig), gleichzeitige Anrufe.

Änderungen an Befehlen und am Anrufablauf gelten sofort für neue Anrufe, ohne laufende Gespräche
zu unterbrechen. Änderungen am SIP-/Netzwerkteil starten den SIP-Server neu.

## Bedienung am Telefon

1. Begrüßung, ggf. PIN-Eingabe (abschließen mit `#`)
2. Menüansage – jede Taste unterbricht die Ansage
3. Code eingeben: eindeutige Codes werden sofort ausgeführt, sonst nach der Wartezeit oder mit `#`
4. `*` wiederholt das Menü, die Assistenten-Taste (Standard `0`) verbindet mit der KI
5. Im Gespräch mit der KI bringt `*` dich zurück ins Menü; „Tschüss“ beendet den Anruf

### Softphone einrichten

- **Linphone, MicroSIP**: ohne Konto einfach `sip:homeassistant@<HA-IP>` wählen (bei anderem
  Port mit `:5070` usw.).
- **Mit Passwort oder Apps, die ein Konto verlangen (z. B. Zoiper)**: ein SIP-Konto anlegen –
  Benutzer = SIP-Benutzer, Domain/Server = `<HA-IP>:<Port>`, Transport UDP. Der SIP Assistant
  nimmt die Registrierung an; anschließend den SIP-Benutzer anrufen.
- **Codecs**: G.711 A-law (PCMA) und µ-law (PCMU), DTMF per RFC 4733 („RFC2833“) oder SIP INFO.
  SRTP/verschlüsselte Medien werden nicht unterstützt – im LAN unkritisch, für Anrufe aus dem
  Internet einen VPN-Zugang nutzen.

## Automationen

Jedes Ereignis erscheint an der Entität **Anruf** (`event.sip_assistant_call`) und zusätzlich als
Bus-Event `sip_assistant_<typ>`:

| Ereignis | Daten |
| --- | --- |
| `call_started`, `call_ended` | `caller`, `caller_name`, `caller_address`, `call_id`, bei Ende `reason`, `duration` |
| `code_entered` | `code`, `command` (oder `null` für unbekannte Codes) |
| `command_executed` | `code`, `command`, `success` |
| `assistant_started`, `pin_failed`, `call_rejected` | Anruferdaten bzw. `reason` |

Beispiel – beliebige Codes ohne eigenen Tastenbefehl auswerten:

```yaml
triggers:
  - trigger: event
    event_type: sip_assistant_code_entered
    event_data:
      code: "4711"
actions:
  - action: lock.unlock
    target:
      entity_id: lock.haustuer
```

## Sicherheit und Datenschutz

- Standardmäßig dürfen nur private Netze anrufen. Leite den SIP-Port **nicht** ungeschützt ins
  Internet weiter.
- Setze ein SIP-Passwort und/oder eine PIN, besonders wenn Befehle Türen oder Alarmanlagen
  steuern.
- Der Assistent sieht nur Entitäten, die für Assist freigegeben sind
  (*Einstellungen → Sprachassistenten → Entitäten freigeben*).
- Audio wird nur während der Assistenten-Phase an OpenAI übertragen, nicht im Tastenmenü.
- Die maximale Gesprächsdauer beendet jeden Anruf nach der eingestellten Zeit.

## Fehlersuche

```yaml
logger:
  logs:
    custom_components.sip_assistant: debug
```

- **Kein Ton / einseitiges Audio**: RTP-Portbereich in der Firewall freigeben; bei Docker
  `network_mode: host`; hinter NAT die angekündigte Adresse setzen.
- **Tasten werden nicht erkannt**: Im Softphone DTMF-Modus „RFC 2833/4733“ oder „SIP INFO“ wählen
  (In-Band-DTMF wird nicht ausgewertet).
- **Setup schlägt fehl, Port belegt**: anderen SIP-Port wählen (z. B. wegen der VoIP-Integration).
- Die Diagnose-Datei (Integrationsseite → ⋮ → Diagnose herunterladen) enthält Einstellungen ohne
  Passwörter/Keys und die aktiven Anrufe.

## Entwicklung

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest tests
.venv/bin/ruff check custom_components tests
```

Aufbau:

| Pfad | Inhalt |
| --- | --- |
| `sip/` | SIP-Parser, SDP, Digest-Auth und der UDP-Server (Transaktionen, Dialoge, Registrar) |
| `rtp/` | RTP-Pakete, getaktete Audiosession, G.711, DTMF (RFC 4733/INFO), Signaltöne |
| `call_session.py` | Ablauf eines Anrufs: Begrüßung, PIN, Tastenmenü, Assistent |
| `voice/` | GPT-Live- und Realtime-Agenten sowie die Brücke zu den HA-LLM-Werkzeugen |
| `config_flow.py` | Einrichtung, Optionen und Tastenbefehle (Config-Subentries) |
