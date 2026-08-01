const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

/** Formats a number as Indian-grouped rupees, e.g. 149900 -> "₹1,49,900" */
export function formatINR(amount: number): string {
  return inr.format(amount);
}

/** Formats a number with Indian digit grouping, no currency symbol. */
export function formatIndianNumber(amount: number): string {
  return new Intl.NumberFormat("en-IN").format(amount);
}

/** Rounds to the nearest whole percent off, given MRP and selling price. */
export function discountPercent(mrp: number, sellingPrice: number): number {
  if (mrp <= 0 || sellingPrice >= mrp) return 0;
  return Math.round(((mrp - sellingPrice) / mrp) * 100);
}

const deliveryDateFormat = new Intl.DateTimeFormat("en-IN", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

/** Formats today + `daysFromNow` as e.g. "Wed, 5 Aug" for the PDP delivery estimate. */
export function formatDeliveryDate(daysFromNow: number): string {
  const date = new Date();
  date.setDate(date.getDate() + daysFromNow);
  return deliveryDateFormat.format(date);
}
