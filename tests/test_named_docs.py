import pytest

from hld_navigator.models import Location
from hld_navigator.named_docs import named_declarations


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A Rust VSS Server - the [Nebula broker](../).", {("component", "Nebula broker")}),
        (
            "The [Stone Feeder](https://example.test) is an example of a CAN data-provider.",
            {("component", "Stone Feeder")},
        ),
        ("## `nebula.signal.v3` gRPC Protocol", {("interface", "nebula.signal.v3")}),
        ("Clients use the NEBULA GRPC API.", {("interface", "NEBULA GRPC API")}),
        (
            "A provider for the sensor `Car.Chassis.Load` updates its value.",
            {("signal", "Car.Chassis.Load")},
        ),
        ("See [Architecture](architecture.md) and `some.setting`.", set()),
        ("A provider may connect to another computer.", set()),
    ],
)
def test_explicit_named_declarations_without_inferred_edges(text, expected):
    entities = named_declarations(text, Location(line=1))
    assert {(e.kind, e.name) for e in entities} == expected
    assert all(e.evidence == text for e in entities)
    assert not any(e.kind == "dependency" for e in entities)
