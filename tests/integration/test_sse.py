import asyncio
import json

from backend.dashboard_api.stream import broadcaster


class _ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


def test_client_receives_decision_within_one_second() -> None:
    async def scenario() -> None:
        broadcaster.reset()
        stream = broadcaster.subscribe(_ConnectedRequest())
        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        broadcaster.publish("decision_made", {"decision_id": "D-live"})
        event = await asyncio.wait_for(pending, timeout=1.0)
        assert event["event"] == "decision_made"
        assert json.loads(event["data"])["decision_id"] == "D-live"
        await stream.aclose()

    asyncio.run(scenario())


def test_last_event_id_replays_only_missed_events() -> None:
    async def scenario() -> None:
        broadcaster.reset()
        first = broadcaster.publish("event_ingested", {"sequence": 1})
        second = broadcaster.publish("decision_made", {"sequence": 2})
        stream = broadcaster.subscribe(
            _ConnectedRequest(), last_event_id=str(first.id)
        )
        event = await asyncio.wait_for(anext(stream), timeout=1.0)
        assert event["id"] == str(second.id)
        assert json.loads(event["data"])["sequence"] == 2
        await stream.aclose()

    asyncio.run(scenario())


def test_five_concurrent_clients_all_receive_the_same_event() -> None:
    async def scenario() -> None:
        broadcaster.reset()
        streams = [broadcaster.subscribe(_ConnectedRequest()) for _ in range(5)]
        pending = [asyncio.create_task(anext(stream)) for stream in streams]
        await asyncio.sleep(0)
        published = broadcaster.publish("decision_made", {"decision_id": "D-five"})
        received = await asyncio.wait_for(asyncio.gather(*pending), timeout=1.0)
        assert [item["id"] for item in received] == [str(published.id)] * 5
        for stream in streams:
            await stream.aclose()

    asyncio.run(scenario())
