import { expect, test } from "@playwright/test";

test("backend decision renders a dismissible grounded cart intervention", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /^add to cart$/i }).first().click();
  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  expect(sessionId).toBeTruthy();

  await expect.poll(async () => {
    const response = await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return 0;
    return (await response.json() as { counters: { cart_adds: number } }).counters.cart_adds;
  }).toBe(1);

  const eventTypes = [
    "REVIEW_OPENED", "REVIEW_OPENED", "REVIEW_OPENED",
    "SIMILAR_PRODUCT_VIEWED", "SIMILAR_PRODUCT_VIEWED", "SIMILAR_PRODUCT_VIEWED",
    "SIMILAR_PRODUCT_VIEWED", "SIMILAR_PRODUCT_VIEWED",
  ];
  const events = eventTypes.map((eventType, index) => ({
    event_id: crypto.randomUUID(),
    event_type: eventType,
    session_id: sessionId,
    product_id: "p-1001",
    sequence_no: index + 3,
    client_timestamp: new Date().toISOString(),
    metadata: eventType === "REVIEW_OPENED"
      ? { source: "PRODUCT_PAGE" }
      : { origin_product_id: "p-1001" },
  }));
  const ingested = await request.post("http://localhost:8000/api/v1/events", {
    data: { events },
  });
  expect(ingested.ok()).toBeTruthy();
  await page.evaluate(({ key, value }) => sessionStorage.setItem(key, value), {
    key: `fk-event-sequence:${sessionId}`,
    value: "10",
  });

  await page.waitForTimeout(3_100);
  const decision = await request.post(
    `http://localhost:8000/api/v1/sessions/${sessionId}/decisions`,
    { data: { trigger: "SIMILAR_PRODUCT_VIEWED", force: true } },
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
