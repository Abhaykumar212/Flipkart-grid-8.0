import { expect, test } from "@playwright/test";

test("add-to-cart persists an ITEM_ADDED_TO_CART event", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const addButton = page.getByRole("button", { name: /^add to cart$/i }).first();
  await expect(addButton).toBeVisible();
  await addButton.click();
  await expect(page.getByTestId("cart-badge")).toHaveText("1");

  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  expect(sessionId).toBeTruthy();

  await expect.poll(async () => {
    const response = await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return 0;
    const state = await response.json() as { counters: { cart_adds: number } };
    return state.counters.cart_adds;
  }).toBeGreaterThanOrEqual(1);
});

test("ten rapid cart additions preserve order and batch efficiently", async ({ page, request }) => {
  const eventBatches: Array<Array<{ event_type: string; sequence_no: number }>> = [];
  page.on("request", (outgoing) => {
    if (outgoing.method() !== "POST" || !outgoing.url().endsWith("/api/v1/events")) return;
    const body = outgoing.postDataJSON() as { events?: Array<{ event_type: string; sequence_no: number }> };
    if (body.events) eventBatches.push(body.events);
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const addButton = page.locator("button[data-card-action]").first();
  for (let index = 0; index < 10; index += 1) await addButton.click();
  await expect(page.getByTestId("cart-badge")).toHaveText("10");

  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  await expect.poll(async () => {
    const response = await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return 0;
    const state = await response.json() as { counters: { cart_adds: number } };
    return state.counters.cart_adds;
  }).toBe(10);

  const cartEvents = eventBatches.flat().filter((event) => event.event_type === "ITEM_ADDED_TO_CART");
  expect(cartEvents).toHaveLength(10);
  expect(cartEvents.map((event) => event.sequence_no)).toEqual(
    [...cartEvents].map((event) => event.sequence_no).sort((left, right) => left - right),
  );
  expect(eventBatches.length).toBeLessThanOrEqual(2);
});

test("the storefront remains usable and buffers events while the API is down", async ({ page }) => {
  await page.route("http://localhost:8000/api/**", (route) => route.abort("failed"));
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /^add to cart$/i }).first().click();

  await expect(page.getByTestId("cart-badge")).toHaveText("1");
  const bufferedTypes = await page.evaluate(() => {
    const events = JSON.parse(localStorage.getItem("fk-event-buffer-v1") ?? "[]") as Array<{
      event_type: string;
    }>;
    return events.map((event) => event.event_type);
  });
  expect(bufferedTypes).toContain("SESSION_STARTED");
  expect(bufferedTypes).toContain("ITEM_ADDED_TO_CART");
});

test("closing the tab beacons SESSION_ENDED", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  await expect.poll(async () => (
    await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`)
  ).status()).toBe(200);

  await page.close();

  await expect.poll(async () => {
    const response = await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return false;
    const state = await response.json() as { session: { ended: boolean } };
    return state.session.ended;
  }).toBe(true);
});

test("a storefront journey updates the server-owned session counters", async ({ page, request }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const search = page.getByRole("searchbox", { name: /search for products/i });
  await search.fill("Apple iPhone 16");
  await search.press("Enter");
  await page.getByRole("link", { name: /view apple iphone 16/i }).first().click();

  await page.getByRole("textbox", { name: /enter delivery pincode/i }).fill("560001");
  await page.getByRole("button", { name: "Check" }).click();
  await page.getByTestId("reviews-section").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("reviews-section")).toBeVisible();
  await page.getByTestId("add-to-cart-button").click();
  await page.getByRole("link", { name: /shopping cart with 1 items/i }).click();

  await page.getByRole("textbox", { name: "Coupon code" }).fill("WELCOME10");
  await page.getByRole("button", { name: "Apply" }).click();
  await page.getByTestId("place-order-button").click();
  await page.getByRole("textbox", { name: "Full name" }).fill("Grid Demo");
  await page.getByRole("textbox", { name: "Email address" }).fill("grid@example.com");
  await page.getByRole("textbox", { name: "Mobile number" }).fill("9876543210");
  await page.getByRole("textbox", { name: "Pincode" }).fill("560001");
  await page.getByRole("textbox", { name: "Address", exact: true }).fill("42 Demo Street");
  await page.getByRole("textbox", { name: "City" }).fill("Bengaluru");
  await page.getByRole("textbox", { name: "State" }).fill("Karnataka");
  await page.getByTestId("save-address-button").click();
  await page.getByTestId("continue-to-payment-button").click();
  await page.getByRole("radio", { name: /credit \/ debit/i }).check();
  await page.getByRole("button", { name: "Simulate payment failure" }).click();
  await page.getByRole("radio", { name: /^UPI/i }).check();
  await page.getByRole("checkbox", { name: /I agree to the demo store terms/i }).check();
  await page.getByTestId("confirm-order-button").click();
  await expect(page.getByTestId("order-confirmation")).toBeVisible();

  const sessionId = await page.evaluate(() => sessionStorage.getItem("fk-session-id-v1"));
  await expect.poll(async () => {
    const response = await request.get(`http://localhost:8000/api/v1/sessions/${sessionId}`);
    if (!response.ok()) return null;
    const state = await response.json() as {
      session: { order_completed: boolean };
      counters: Record<string, number>;
    };
    return {
      orderCompleted: state.session.order_completed,
      searches: state.counters.searches,
      productViews: state.counters.product_views,
      reviewOpens: state.counters.review_opens,
      reviewDwellRecorded: state.counters.review_dwell_ms > 0,
      deliveryChecks: state.counters.delivery_checks,
      cartAdds: state.counters.cart_adds,
      cartViews: state.counters.cart_views,
      couponSearches: state.counters.coupon_searches,
      checkoutStarts: state.counters.checkout_starts,
      checkoutStep: state.counters.checkout_max_step,
      paymentFailures: state.counters.payment_failures,
      paymentChanges: state.counters.payment_method_changes,
    };
  }).toMatchObject({
    orderCompleted: true,
    searches: 1,
    productViews: 1,
    reviewOpens: 1,
    reviewDwellRecorded: true,
    deliveryChecks: 1,
    cartAdds: 1,
    cartViews: 1,
    couponSearches: 1,
    checkoutStarts: 1,
    checkoutStep: 3,
    paymentFailures: 1,
    paymentChanges: 1,
  });
});
