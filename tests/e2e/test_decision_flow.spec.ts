import { expect, test } from "@playwright/test";

const apiBase = process.env.E2E_API_BASE ?? "http://localhost:8000";

test("backend decision renders a dismissible grounded cart intervention", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /^add to cart$/i }).first().click();
  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  expect(sessionId).toBeTruthy();

  await expect.poll(async () => {
    const response = await request.get(`${apiBase}/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return 0;
    return (await response.json() as { counters: { cart_adds: number } }).counters.cart_adds;
  }).toBe(1);

  const eventSpecs = [
    { eventType: "REVIEW_OPENED", productId: "p-1001", metadata: { source: "PRODUCT_PAGE" } },
    { eventType: "REVIEW_DWELL_RECORDED", productId: "p-1001", metadata: { dwell_ms: 40_000 } },
    { eventType: "REVIEW_OPENED", productId: "p-1001", metadata: { source: "PRODUCT_PAGE" } },
    { eventType: "REVIEW_DWELL_RECORDED", productId: "p-1001", metadata: { dwell_ms: 40_000 } },
    { eventType: "REVIEW_OPENED", productId: "p-1001", metadata: { source: "PRODUCT_PAGE" } },
    { eventType: "REVIEW_DWELL_RECORDED", productId: "p-1001", metadata: { dwell_ms: 40_000 } },
    ...["p-1002", "p-1003", "p-1004", "p-1005", "p-1006"].map((productId) => ({
      eventType: "SIMILAR_PRODUCT_VIEWED",
      productId,
      metadata: { origin_product_id: "p-1001" },
    })),
    { eventType: "CART_VIEWED", metadata: { cart_value: 71_999, item_count: 1 } },
  ];
  const events = eventSpecs.map(({ eventType, productId, metadata }, index) => ({
    event_id: crypto.randomUUID(),
    event_type: eventType,
    session_id: sessionId,
    ...(productId ? { product_id: productId } : {}),
    sequence_no: index + 3,
    client_timestamp: new Date().toISOString(),
    metadata,
  }));
  const ingested = await request.post(`${apiBase}/api/v1/events`, {
    data: { events },
  });
  expect(ingested.ok()).toBeTruthy();
  await page.evaluate(({ key, value }) => sessionStorage.setItem(key, value), {
    key: `fk-event-sequence:${sessionId}`,
    value: String(events.length + 2),
  });

  await page.waitForTimeout(3_100);
  const decision = await request.post(
    `${apiBase}/api/v1/sessions/${sessionId}/decisions`,
    { data: { trigger: "CART_VIEWED", force: true } },
  );
  expect(decision.ok()).toBeTruthy();
  const decisionBody = await decision.json() as {
    decision: string;
    decision_id: string;
    recommended_intervention: { decision_id?: string };
  };
  expect(decisionBody.decision).toBe("INTERVENE");
  expect(decisionBody.recommended_intervention.decision_id).toBe(decisionBody.decision_id);

  await page.getByRole("link", { name: /shopping cart with 1 items/i }).click();
  const card = page.getByTestId("intervention-inline-card");
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Dismiss recommendation" }).click();
  await expect(card).toBeHidden();
});
