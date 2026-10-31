"""End-to-end tests: a scripted SIP phone calls Home Assistant."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from custom_components.sip_assistant.const import (
    CONF_ACTION_TYPE,
    CONF_ALLOWED_NETWORKS,
    CONF_MAX_CALLS,
    CONF_PIN,
    CONF_SIP_PASSWORD,
    DOMAIN,
)

from .helpers import SENSOR, command, setup, update_options, wait_for
from .phone import FakePhone


@pytest.fixture
def entry_with_command(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> MockConfigEntry:
    update_options(
        hass,
        mock_config_entry,
        commands=[
            command("1", "Garage"),
            command(
                "21",
                "Temperature",
                **{CONF_ACTION_TYPE: "announcement", "response": "It is {{ 20 + 1 }} degrees"},
            ),
        ],
    )
    return mock_config_entry


async def test_keypad_command(
    hass: HomeAssistant, entry_with_command: MockConfigEntry, sip_port: int
) -> None:
    """A caller runs a command with the keypad and hangs up."""
    script_calls = async_mock_service(hass, "script", "turn_on")
    entered = async_capture_events(hass, f"{DOMAIN}_code_entered")
    executed = async_capture_events(hass, f"{DOMAIN}_command_executed")
    ended = async_capture_events(hass, f"{DOMAIN}_call_ended")
    await setup(hass, entry_with_command)
    assert hass.states.get(SENSOR).state == "idle"

    async with FakePhone(sip_port) as phone:
        response = await phone.call()
        assert response.get("Contact") == f"<sip:homeassistant@127.0.0.1:{sip_port}>"
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
        state = hass.states.get(SENSOR)
        assert state.attributes["caller"] == "1001"
        assert state.attributes["caller_name"] == "Test Phone"

        # The menu prompt tone is sent as audio.
        await asyncio.wait_for(phone.rtp.queue.get(), 2)

        phone.press("1")
        await wait_for(lambda: len(script_calls) == 1)
        assert script_calls[0].data["entity_id"] == "script.garage"
        assert script_calls[0].data["variables"]["caller"] == "1001"
        await wait_for(lambda: len(executed) == 1)
        assert executed[0].data["command"] == "Garage"
        assert executed[0].data["success"] is True

        phone.press("2")
        await asyncio.sleep(0.1)
        phone.press("1")  # "21" completes immediately (no longer code)
        await wait_for(lambda: len(entered) == 2)
        assert entered[1].data["code"] == "21"

        phone.press("9")  # unknown code
        await wait_for(lambda: len(entered) == 3)
        assert entered[2].data["command"] is None

        await phone.hang_up()

    await wait_for(lambda: hass.states.get(SENSOR).state == "idle")
    await wait_for(lambda: len(ended) == 1)
    assert ended[0].data["reason"] == "remote_hangup"
    assert hass.states.get("sensor.sip_assistant_last_caller").state == "Test Phone (1001)"
    event_state = hass.states.get("event.sip_assistant_call")
    assert event_state.attributes["event_type"] == "call_ended"

    assert await hass.config_entries.async_unload(entry_with_command.entry_id)


async def test_pin_and_hangup_button(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """A PIN is required before the menu; the button ends the call."""
    update_options(hass, mock_config_entry, call={CONF_PIN: "4711"})
    failed = async_capture_events(hass, f"{DOMAIN}_pin_failed")
    await setup(hass, mock_config_entry)

    async with FakePhone(sip_port) as phone:
        await phone.call()
        await wait_for(lambda: hass.states.get(SENSOR).state == "pin")
        phone.press("4711#")
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")

        await hass.services.async_call(
            "button", "press", {"entity_id": "button.sip_assistant_hang_up"}, blocking=True
        )
        bye = await phone.expect_request("BYE")
        phone.reply(bye, 200)
    await wait_for(lambda: hass.states.get(SENSOR).state == "idle")

    async with FakePhone(sip_port) as phone:
        await phone.call()
        await wait_for(lambda: hass.states.get(SENSOR).state == "pin")
        for _ in range(3):
            phone.press("0000#")
            await asyncio.sleep(0.6)
        bye = await phone.expect_request("BYE", timeout=10)
        phone.reply(bye, 200)
    assert len(failed) == 1


async def test_digest_authentication(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """With a password, calls must authenticate."""
    hass.config_entries.async_update_entry(
        mock_config_entry, data={**mock_config_entry.data, CONF_SIP_PASSWORD: "geheim"}
    )
    await setup(hass, mock_config_entry)

    async with FakePhone(sip_port) as phone:
        invite = phone.invite()
        challenge = await phone.expect_response(401)
        phone.ack(invite, challenge)
        wrong = phone.authorization(challenge, "homeassistant", "falsch", invite.uri)
        invite = phone.invite(wrong)
        challenge = await phone.expect_response(401)
        phone.ack(invite, challenge)

        authorization = phone.authorization(challenge, "homeassistant", "geheim", invite.uri)
        await phone.call(authorization)
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
        await phone.hang_up()


async def test_rejections_and_out_of_dialog_requests(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """Busy, unsupported media, OPTIONS and REGISTER."""
    update_options(hass, mock_config_entry, network={CONF_MAX_CALLS: 1})
    rejected = async_capture_events(hass, f"{DOMAIN}_call_rejected")
    await setup(hass, mock_config_entry)

    async with FakePhone(sip_port) as first, FakePhone(sip_port, user="1002") as second:
        await first.call()
        second.invite()
        await second.expect_response(486)

        third = FakePhone(sip_port, user="1003")
        async with third:
            third.invite(codecs="9")
            await third.expect_response(486)  # still busy: capacity is checked first

        options = first.request("OPTIONS", in_dialog=False)
        first.send(options)
        response = await first.expect_response(200)
        assert "INVITE" in (response.get("Allow") or "")

        register = second.request("REGISTER", in_dialog=False)
        register.add("Expires", "120")
        second.send(register)
        response = await second.expect_response(200)
        assert response.get("Expires") == "120"
        assert "expires=120" in (response.get("Contact") or "")

        message = second.request("MESSAGE", in_dialog=False)
        second.send(message)
        await second.expect_response(405)
        await first.hang_up()

    assert [event.data["reason"] for event in rejected] == ["busy", "busy"]

    async with FakePhone(sip_port) as phone:
        phone.invite(codecs="9")
        await phone.expect_response(488)


async def test_forbidden_network(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """Calls from outside the allowed networks are rejected."""
    update_options(hass, mock_config_entry, network={CONF_ALLOWED_NETWORKS: "10.0.0.0/8"})
    await setup(hass, mock_config_entry)
    async with FakePhone(sip_port) as phone:
        phone.invite()
        await phone.expect_response(403)


async def test_unload_hangs_up(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """Unloading the entry ends active calls with BYE."""
    await setup(hass, mock_config_entry)
    async with FakePhone(sip_port) as phone:
        await phone.call()
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
        unload = hass.async_create_task(
            hass.config_entries.async_unload(mock_config_entry.entry_id)
        )
        bye = await phone.expect_request("BYE")
        phone.reply(bye, 200)
        assert await unload
