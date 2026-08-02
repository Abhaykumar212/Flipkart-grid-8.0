import pytest
from pydantic import ValidationError

from backend.domain.events import EventEnvelope, EventType
from tests.event_factories import event_payload


@pytest.mark.parametrize("event_type", list(EventType))
def test_all_event_types_validate_with_their_metadata(event_type):
    event = EventEnvelope.model_validate(event_payload(event_type))
    assert event.event_type == event_type


def test_metadata_rejects_extra_or_invalid_fields_with_a_field_path():
    payload = event_payload(EventType.ITEM_ADDED_TO_CART)
    payload["metadata"]["invented"] = True
    with pytest.raises(ValidationError) as captured:
        EventEnvelope.model_validate(payload)
    assert any("invented" in str(error["loc"]) for error in captured.value.errors())

    payload = event_payload(EventType.PRODUCT_VIEWED)
    payload["metadata"]["source"] = "MAGIC"
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(payload)


def test_envelope_reports_event_type_and_required_product_paths():
    payload = event_payload(EventType.SEARCH_PERFORMED)
    payload["event_type"] = "INVENTED"
    with pytest.raises(ValidationError) as invalid_type:
        EventEnvelope.model_validate(payload)
    assert invalid_type.value.errors()[0]["loc"] == ("event_type",)

    payload = event_payload(EventType.PRODUCT_VIEWED)
    del payload["product_id"]
    with pytest.raises(ValidationError) as missing_product:
        EventEnvelope.model_validate(payload)
    assert missing_product.value.errors()[0]["loc"] == ("product_id",)
