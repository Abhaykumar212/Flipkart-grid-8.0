import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { eventClient } from "../lib/events";
import { SessionProvider, useSession } from "./SessionContext";

function SessionProbe() {
  const { sessionId } = useSession();
  return <span>{sessionId}</span>;
}

describe("SessionProvider", () => {
  it("creates a session, queues SESSION_STARTED, and beacons SESSION_ENDED", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ session_id: "created" }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    ));
    const sendBeacon = vi.fn(() => true);
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: sendBeacon,
    });

    render(<SessionProvider><SessionProbe /></SessionProvider>);
    const sessionId = screen.getByText(/^S-/).textContent;
    expect(sessionId).toBeTruthy();
    expect(eventClient.pendingEvents()[0]).toMatchObject({
      event_type: "SESSION_STARTED",
      session_id: sessionId,
      sequence_no: 1,
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const pagehide = new Event("pagehide") as PageTransitionEvent;
    Object.defineProperty(pagehide, "persisted", { value: false });
    window.dispatchEvent(pagehide);

    expect(eventClient.pendingEvents().at(-1)).toMatchObject({
      event_type: "SESSION_ENDED",
      session_id: sessionId,
      sequence_no: 2,
    });
    expect(sendBeacon).toHaveBeenCalledOnce();
    fetchMock.mockRestore();
  });
});
