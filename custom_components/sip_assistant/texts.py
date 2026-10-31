"""Spoken phrases and default prompts in the supported languages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Phrases:
    """Phrases used during a call."""

    greeting: str
    enter_pin: str
    wrong_pin: str
    pin_locked: str
    menu_item: str
    menu_assistant: str
    menu_repeat: str
    menu_empty: str
    unknown_code: str
    command_done: str
    command_failed: str
    assistant_unavailable: str
    assistant_not_configured: str
    no_input: str
    max_duration: str
    goodbye: str
    default_prompt: str
    style_rules: str
    end_call_rule: str
    menu_hint: str
    caller_info: str
    commands_intro: str
    greet_instruction: str
    live_delegation_rules: str
    backend_rules: str
    end_call_description: str
    command_tool_description: str


GERMAN = Phrases(
    greeting="Hallo, hier ist Home Assistant.",
    enter_pin="Bitte gib deine PIN ein und bestätige mit der Rautetaste.",
    wrong_pin="Die PIN ist leider falsch.",
    pin_locked="Zu viele Fehlversuche. Auf Wiederhören.",
    menu_item="Für {name} drücke {code}.",
    menu_assistant="Für den Sprachassistenten drücke {code}.",
    menu_repeat="Mit der Sterntaste hörst du das Menü erneut.",
    menu_empty="Es sind noch keine Tastenbefehle eingerichtet.",
    unknown_code="Den Code {code} kenne ich nicht.",
    command_done="{name} wurde ausgeführt.",
    command_failed="{name} konnte nicht ausgeführt werden.",
    assistant_unavailable="Der Sprachassistent ist gerade nicht erreichbar.",
    assistant_not_configured="Der Sprachassistent ist nicht eingerichtet.",
    no_input="Ich habe keine Eingabe erhalten. Auf Wiederhören.",
    max_duration="Die maximale Gesprächsdauer ist erreicht. Auf Wiederhören.",
    goodbye="Auf Wiederhören.",
    default_prompt=(
        "Du bist der Sprachassistent von Home Assistant und sprichst am Telefon "
        "mit einem Bewohner. Antworte kurz, freundlich und natürlich auf Deutsch."
    ),
    style_rules=(
        "Das Gespräch läuft über eine Telefonleitung. Antworte in ein bis zwei "
        "kurzen Sätzen ohne Aufzählungen, Markdown, Emojis oder URLs. Bestätige "
        "ausgeführte Aktionen knapp und erfinde keine Ergebnisse."
    ),
    end_call_rule=(
        "Wenn der Anrufer das Gespräch beenden möchte, verabschiede dich kurz "
        "und rufe danach die Funktion end_call auf."
    ),
    menu_hint="Mit der Sterntaste kommt der Anrufer jederzeit zurück ins Tastenmenü.",
    caller_info="Anrufer: {caller}.",
    commands_intro=(
        "Zusätzlich gibt es diese Telefon-Befehle, die du mit run_phone_command ausführen kannst:"
    ),
    greet_instruction=(
        "Begrüße den Anrufer jetzt kurz auf Deutsch und frage, wie du helfen "
        "kannst. Warte danach auf seine Antwort."
    ),
    live_delegation_rules=(
        "Gib alle Anfragen zum Zuhause (Geräte, Zustände, Aktionen, Befehle) "
        "sowie den Wunsch aufzulegen an das Backend weiter und erfinde keine "
        "Ergebnisse."
    ),
    backend_rules=(
        "Du unterstützt einen Sprachassistenten in einem laufenden Telefonat. "
        "Transkripte können Fehler enthalten; frage nach, wenn etwas unklar ist. "
        "Führe gewünschte Aktionen mit den Werkzeugen aus und melde das Ergebnis "
        "in ein bis zwei kurzen Sätzen auf Deutsch. Melde eine Aktion erst als "
        "erledigt, wenn das Werkzeug Erfolg bestätigt. Möchte der Anrufer "
        "auflegen, rufe end_call auf."
    ),
    end_call_description=(
        "Beendet das Telefonat. Erst aufrufen, nachdem du dich verabschiedet hast "
        "oder der Anrufer ausdrücklich auflegen möchte."
    ),
    command_tool_description="Führt einen eingerichteten Telefon-Befehl aus.",
)

ENGLISH = Phrases(
    greeting="Hello, this is Home Assistant.",
    enter_pin="Please enter your PIN followed by the hash key.",
    wrong_pin="That PIN is not correct.",
    pin_locked="Too many failed attempts. Goodbye.",
    menu_item="For {name}, press {code}.",
    menu_assistant="For the voice assistant, press {code}.",
    menu_repeat="Press star to hear this menu again.",
    menu_empty="No keypad commands have been set up yet.",
    unknown_code="I don't know the code {code}.",
    command_done="{name} has been executed.",
    command_failed="{name} could not be executed.",
    assistant_unavailable="The voice assistant is not reachable right now.",
    assistant_not_configured="The voice assistant has not been set up.",
    no_input="I did not receive any input. Goodbye.",
    max_duration="The maximum call duration has been reached. Goodbye.",
    goodbye="Goodbye.",
    default_prompt=(
        "You are the Home Assistant voice assistant talking to a resident on the "
        "phone. Answer briefly, friendly and naturally."
    ),
    style_rules=(
        "This conversation runs over a phone line. Answer in one or two short "
        "sentences without lists, Markdown, emojis or URLs. Confirm actions "
        "briefly and never make up results."
    ),
    end_call_rule=(
        "When the caller wants to end the call, say a short goodbye and then "
        "call the end_call function."
    ),
    menu_hint="The caller can press the star key at any time to return to the keypad menu.",
    caller_info="Caller: {caller}.",
    commands_intro="You can also run these phone commands with run_phone_command:",
    greet_instruction=(
        "Greet the caller now in English and ask how you can help. Then pause and listen."
    ),
    live_delegation_rules=(
        "Delegate every request about the home (devices, states, actions, "
        "commands) and the wish to hang up to the backend, and never make up "
        "results."
    ),
    backend_rules=(
        "You support a voice assistant during a live phone call. Transcripts can "
        "contain mistakes; ask when something is unclear. Carry out requested "
        "actions with the tools and report the outcome in one or two short "
        "sentences. Only report an action as done once the tool confirms "
        "success. If the caller wants to hang up, call end_call."
    ),
    end_call_description=(
        "Ends the phone call. Only call it after saying goodbye or when the "
        "caller explicitly wants to hang up."
    ),
    command_tool_description="Runs one of the configured phone commands.",
)


def phrases_for(language: str | None) -> Phrases:
    """Return the phrases for a language (German or English fallback)."""
    if language and language.lower().split("-")[0] == "de":
        return GERMAN
    return ENGLISH


def spell_code(code: str) -> str:
    """Spell a keypad code digit by digit so TTS does not read it as a number."""
    return " ".join(code)
