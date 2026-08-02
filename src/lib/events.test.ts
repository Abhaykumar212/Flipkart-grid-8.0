import { afterEach, describe, expect, it, vi } from "vitest";
import { EventClient, type EventEnvelope } from "./events";

class MemoryStorage {
  private readonly values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

function deterministicUuid() {
  let value = 0;
  return () => `00000000-0000-4000-8000-${String(++value).padStart(12, "0")}`;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("EventClient", () => {
  it("batches events after 500ms with a gapless per-session sequence", async () => {
    vi.useFakeTimers();
    const posted: EventEnvelope[][] = [];
    const client = new EventClient({
      localStorage: new MemoryStorage(),
      sessionStorage: new MemoryStorage(),
      randomUUID: deterministicUuid(),
      now: () => new Date("2026-08-02T08:00:00Z"),
      postEvents: async (events) => {
        posted.push(events);
        return { accepted: events.length, duplicates: 0 };
      },
    });
    client.setSession("S-test");

    client.emit("SEARCH_PERFORMED", {
      metadata: { query: "phone", result_count: 10, sort_order: "RELEVANCE" },
    });
    client.emit("CART_VIEWED", { metadata: { cart_value: 1000, item_count: 1 } });

    expect(posted).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(500);
    expect(posted).toHaveLength(1);
    expect(posted[0].map((event) => event.sequence_no)).toEqual([1, 2]);
    expect(client.pendingEvents()).toHaveLength(0);
  });

  it("flushes immediately at ten events", async () => {
    vi.useFakeTimers();
    const postEvents = vi.fn(async (events: EventEnvelope[]) => ({
      accepted: events.length,
      duplicates: 0,
    }));
    const client = new EventClient({
      localStorage: new MemoryStorage(),
      sessionStorage: new MemoryStorage(),
      randomUUID: deterministicUuid(),
      postEvents,
    });
    client.setSession("S-ten");

    for (let index = 0; index < 10; index += 1) {
      client.emit("SEARCH_PERFORMED", {
        metadata: { query: `phone-${index}`, result_count: 1, sort_order: "RELEVANCE" },
      });
    }
    await vi.advanceTimersByTimeAsync(0);

    expect(postEvents).toHaveBeenCalledTimes(1);
    expect(postEvents.mock.calls[0][0]).toHaveLength(10);
  });

  it("retries the same id after a network failure and restores the offline buffer", async () => {
    vi.useFakeTimers();
    const localStorage = new MemoryStorage();
    const sessionStorage = new MemoryStorage();
    const attempts: string[] = [];
    let online = false;
    const postEvents = async (events: EventEnvelope[]) => {
      attempts.push(events[0].event_id);
      if (!online) throw new TypeError("offline");
      return { accepted: events.length, duplicates: 0 };
    };
    const firstClient = new EventClient({
      localStorage,
      sessionStorage,
      randomUUID: deterministicUuid(),
      postEvents,
    });
    firstClient.setSession("S-offline");
    const emitted = firstClient.emit("CART_VIEWED", {
      metadata: { cart_value: 500, item_count: 1 },
    });

    await vi.advanceTimersByTimeAsync(500);
    expect(firstClient.pendingEvents()).toHaveLength(1);

    firstClient.resetForTests();
    // resetForTests intentionally clears storage, so recreate the persisted failure explicitly.
    localStorage.setItem("fk-event-buffer-v1", JSON.stringify([emitted]));
    const restoredClient = new EventClient({ localStorage, sessionStorage, postEvents });
    restoredClient.setSession("S-offline");
    expect(restoredClient.pendingEvents()[0].event_id).toBe(emitted?.event_id);

    online = true;
    await vi.advanceTimersByTimeAsync(500);
    expect(attempts).toEqual([emitted?.event_id, emitted?.event_id]);
    expect(restoredClient.pendingEvents()).toHaveLength(0);
  });

  it("caps the offline buffer without consuming sequence numbers for dropped events", () => {
    vi.useFakeTimers();
    const client = new EventClient({
      localStorage: new MemoryStorage(),
      sessionStorage: new MemoryStorage(),
      randomUUID: deterministicUuid(),
      postEvents: async () => {
        throw new TypeError("offline");
      },
    });
    client.setSession("S-cap");
    for (let index = 0; index < 201; index += 1) {
      client.emit("SEARCH_PERFORMED", {
        metadata: { query: `q-${index}`, result_count: 0, sort_order: "RELEVANCE" },
      });
    }

    expect(client.pendingEvents()).toHaveLength(200);
    expect(client.pendingEvents().at(-1)?.sequence_no).toBe(200);
  });
});
