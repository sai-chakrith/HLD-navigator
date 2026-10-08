import pytest

from hld_navigator.extraction import extract


@pytest.mark.parametrize(
    "recipients",
    [
        "the Cluster component and the Logger component",
        "Cluster, Logger and Gateway components",
        "Cluster, Logger, and Gateway components",
    ],
)
def test_every_recipient_is_preserved(recipients):
    text = f"The Engine component provides the Torque interface to {recipients}."
    _, entities, warnings = extract("recipients.md", text.encode())
    expected = {"Cluster", "Logger"} | ({"Gateway"} if "Gateway" in recipients else set())
    edges = [e for e in entities if e.kind == "dependency"]
    assert {e.attributes["target"] for e in edges} == expected
    assert all(e.attributes["source"] == "Engine" for e in edges)
    assert not warnings


def test_multiple_senders_and_subsequent_clause():
    text = (
        "The Engine component receives the Brake interface from ABS and BrakeController "
        "components and sends the Torque interface to Cluster and Logger components."
    )
    _, entities, warnings = extract("peers.md", text.encode())
    edges = [e.attributes for e in entities if e.kind == "dependency"]
    assert {(e["source"], e["target"]) for e in edges} == {
        ("ABS", "Engine"),
        ("BrakeController", "Engine"),
        ("Engine", "Cluster"),
        ("Engine", "Logger"),
    }
    assert not warnings


@pytest.mark.parametrize(
    "unit", ["m/s^2", "N·m", "kg m^2 / s^3", "1/s", "m s⁻²", "°C", "rad/s", "m/s**2"]
)
def test_complete_unit_expression(unit):
    _, entities, warnings = extract(
        "units.md", f"The Acceleration signal has type float32 and unit {unit}.".encode()
    )
    signal = next(e for e in entities if e.kind == "signal")
    assert signal.attributes["unit"] == unit
    assert not warnings


def test_plural_units_and_outer_whitespace():
    _, entities, warnings = extract(
        "units.md", b"The Acceleration signal has type float32 with units kg m^2 / s^3   ."
    )
    signal = next(e for e in entities if e.kind == "signal")
    assert signal.attributes["unit"] == "kg m^2 / s^3"
    assert not warnings
