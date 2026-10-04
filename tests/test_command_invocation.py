import pytest

from anka.core.invocation import invoke_command_handler


def test_command_is_given_to_handler_that_accepts_it():
    assert invoke_command_handler(lambda command: command.upper(), "merhaba") == "MERHABA"


def test_no_argument_handler_is_called_without_command():
    calls = []

    def handler():
        calls.append("called")
        return "tamam"

    assert invoke_command_handler(handler, "atla") == "tamam"
    assert calls == ["called"]


def test_internal_type_error_is_not_mistaken_for_wrong_signature():
    def handler(command):
        raise TypeError("iç hata")

    with pytest.raises(TypeError, match="iç hata"):
        invoke_command_handler(handler, "komut")
