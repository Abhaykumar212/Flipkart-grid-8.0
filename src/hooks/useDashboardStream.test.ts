import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDashboardStream } from "./useDashboardStream";

type Listener = (event: Event) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  onopen: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  private listeners = new Map<string, Set<Listener>>();

  constructor(url: string | URL) {
    this.url = String(url);
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    const listeners = this.listeners.get(type) ?? new Set<Listener>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: Listener) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    this.closed = true;
  }

  open() {
    this.onopen?.(new Event("open"));
  }

  fail() {
    this.onerror?.(new Event("error"));
  }

  emit(type: string, data: Record<string, unknown>, id: string) {
    const event = new MessageEvent(type, {
      data: JSON.stringify(data),
      lastEventId: id,
    });
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }
}

describe("useDashboardStream", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("subscribes to named events and exposes their server event ID", () => {
    const onEvent = vi.fn();
    const onOpen = vi.fn();
    const { result, unmount } = renderHook(() => useDashboardStream(onEvent, onOpen));
    const source = FakeEventSource.instances[0];
    expect(source.url).toBe("http://localhost:8000/api/v1/dashboard/stream");

    act(() => source.open());
    expect(result.current.status).toBe("connected");
    expect(onOpen).toHaveBeenCalledOnce();

    act(() => source.emit("decision_made", { decision_id: "D-1" }, "42"));
    expect(result.current.lastEvent).toEqual({
      id: "42",
      type: "decision_made",
      data: { decision_id: "D-1" },
    });
    expect(result.current.eventCount).toBe(1);
    expect(onEvent).toHaveBeenCalledWith(result.current.lastEvent);

    unmount();
    expect(source.closed).toBe(true);
  });

  it("leaves the native EventSource open so it reconnects after an error", () => {
    const onOpen = vi.fn();
    const { result } = renderHook(() => useDashboardStream(undefined, onOpen));
    const source = FakeEventSource.instances[0];

    act(() => source.open());
    act(() => source.fail());
    expect(result.current.status).toBe("reconnecting");
    expect(source.closed).toBe(false);
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => source.open());
    expect(result.current.status).toBe("connected");
    expect(onOpen).toHaveBeenCalledTimes(2);
  });
});
