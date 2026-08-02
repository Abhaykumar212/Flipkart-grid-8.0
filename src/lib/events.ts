import { apiPost, apiUrl } from "./api";

export const EVENT_TYPES = [
  "SESSION_STARTED",
  "SEARCH_PERFORMED",
  "PRODUCT_VIEWED",
  "REVIEW_OPENED",
  "REVIEW_DWELL_RECORDED",
  "SIMILAR_PRODUCT_VIEWED",
  "PRODUCT_COMPARED",
  "ITEM_ADDED_TO_CART",
  "ITEM_REMOVED_FROM_CART",
  "CART_VIEWED",
  "DELIVERY_CHECKED",
  "COUPON_SEARCHED",
  "CHECKOUT_STARTED",
  "CHECKOUT_STEP_VIEWED",
  "PAYMENT_FAILED",
  "PAYMENT_METHOD_CHANGED",
  "INTERVENTION_SHOWN",
  "INTERVENTION_CLICKED",
  "INTERVENTION_DISMISSED",
  "ORDER_COMPLETED",
  "SESSION_ENDED",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];

export interface EventMetadataMap {
  SESSION_STARTED: { device_type: "MOBILE" | "DESKTOP"; referral_source: string; viewport_width: number };
  SEARCH_PERFORMED: { query: string; result_count: number; sort_order: string };
  PRODUCT_VIEWED: { source: "SEARCH" | "RAIL" | "CATEGORY" | "DIRECT" };
  REVIEW_OPENED: { source: string };
  REVIEW_DWELL_RECORDED: { dwell_ms: number };
  SIMILAR_PRODUCT_VIEWED: { origin_product_id: string };
  PRODUCT_COMPARED: { compared_with: string[] };
  ITEM_ADDED_TO_CART: { quantity: number; unit_price: number; variant?: string | null };
  ITEM_REMOVED_FROM_CART: { quantity: number };
  CART_VIEWED: { cart_value: number; item_count: number };
  DELIVERY_CHECKED: { pincode: string; estimated_days: number; available: boolean };
  COUPON_SEARCHED: { code?: string | null; applied: boolean };
  CHECKOUT_STARTED: { cart_value: number; item_count: number };
  CHECKOUT_STEP_VIEWED: { step: 1 | 2 | 3; step_name: string };
  PAYMENT_FAILED: { method: string; reason_code: string; attempt_no: number };
  PAYMENT_METHOD_CHANGED: { from_method: string; to_method: string };
  INTERVENTION_SHOWN: { decision_id: string; intervention_id: string; surface: string };
  INTERVENTION_CLICKED: { decision_id: string; intervention_id: string };
  INTERVENTION_DISMISSED: { decision_id: string; intervention_id: string };
  ORDER_COMPLETED: { order_id: string; order_value: number; payment_method: string };
  SESSION_ENDED: { reason: "EXPLICIT" | "TIMEOUT" | "UNLOAD" };
}

type ProductEventType =
  | "PRODUCT_VIEWED"
  | "REVIEW_OPENED"
  | "REVIEW_DWELL_RECORDED"
  | "SIMILAR_PRODUCT_VIEWED"
  | "PRODUCT_COMPARED"
  | "ITEM_ADDED_TO_CART"
  | "ITEM_REMOVED_FROM_CART"
  | "DELIVERY_CHECKED";

type ProductFields<T extends EventType> = T extends ProductEventType
  ? { productId: string }
  : { productId?: never };

export type EventInput<T extends EventType> = ProductFields<T> & {
  metadata: EventMetadataMap[T];
  userId?: string;
};

export interface EventEnvelope {
  event_id: string;
  event_type: EventType;
  session_id: string;
  user_id?: string;
  product_id?: string;
  sequence_no: number;
  client_timestamp: string;
  metadata: EventMetadataMap[EventType];
}

interface EventAck {
  accepted: number;
  duplicates: number;
}

interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

interface EventClientOptions {
  localStorage?: StorageLike;
  sessionStorage?: StorageLike;
  postEvents?: (events: EventEnvelope[]) => Promise<EventAck>;
  randomUUID?: () => string;
  now?: () => Date;
}

const BUFFER_KEY = "fk-event-buffer-v1";
const SEQUENCE_PREFIX = "fk-event-sequence:";
const FLUSH_DELAY_MS = 500;
const MAX_BATCH_SIZE = 10;
const MAX_BEACON_BATCH_SIZE = 50;
const MAX_BUFFER_SIZE = 200;
const MAX_RETRY_DELAY_MS = 30_000;

function browserStorage(name: "localStorage" | "sessionStorage"): StorageLike | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    return window[name];
  } catch {
    return undefined;
  }
}

function readBuffer(storage?: StorageLike): EventEnvelope[] {
  if (!storage) return [];
  try {
    const parsed: unknown = JSON.parse(storage.getItem(BUFFER_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item): item is EventEnvelope => (
        typeof item === "object"
        && item !== null
        && typeof (item as EventEnvelope).event_id === "string"
        && typeof (item as EventEnvelope).session_id === "string"
      ))
      .slice(0, MAX_BUFFER_SIZE);
  } catch {
    return [];
  }
}

export class EventClient {
  private readonly localStorage?: StorageLike;
  private readonly sessionStorage?: StorageLike;
  private readonly postEvents: (events: EventEnvelope[]) => Promise<EventAck>;
  private readonly randomUUID: () => string;
  private readonly now: () => Date;
  private readonly listeners = new Set<(events: readonly EventEnvelope[]) => void>();
  private readonly memorySequences = new Map<string, number>();
  private queue: EventEnvelope[];
  private sessionId: string | null = null;
  private userId: string | undefined;
  private timer: number | null = null;
  private inFlight: Promise<void> | null = null;
  private retryCount = 0;
  private paused = false;

  constructor(options: EventClientOptions = {}) {
    this.localStorage = options.localStorage ?? browserStorage("localStorage");
    this.sessionStorage = options.sessionStorage ?? browserStorage("sessionStorage");
    this.postEvents = options.postEvents ?? ((events) => (
      apiPost<EventAck>("/api/v1/events", { events })
    ));
    this.randomUUID = options.randomUUID ?? (() => crypto.randomUUID());
    this.now = options.now ?? (() => new Date());
    this.queue = readBuffer(this.localStorage);
  }

  setSession(sessionId: string, userId?: string): void {
    this.sessionId = sessionId;
    this.userId = userId;
    if (this.queue.length > 0) this.scheduleFlush(FLUSH_DELAY_MS);
  }

  subscribe(listener: (events: readonly EventEnvelope[]) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  pause(): void {
    this.paused = true;
    if (this.timer !== null && typeof window !== "undefined") window.clearTimeout(this.timer);
    this.timer = null;
  }

  resume(): void {
    this.paused = false;
    if (this.queue.length > 0) this.scheduleFlush(0);
  }

  emit<T extends EventType>(eventType: T, input: EventInput<T>): EventEnvelope | null {
    if (!this.sessionId || this.queue.length >= MAX_BUFFER_SIZE) return null;
    const envelope: EventEnvelope = {
      event_id: this.randomUUID(),
      event_type: eventType,
      session_id: this.sessionId,
      sequence_no: this.nextSequence(this.sessionId),
      client_timestamp: this.now().toISOString(),
      metadata: input.metadata,
      ...(input.userId ?? this.userId ? { user_id: input.userId ?? this.userId } : {}),
      ...(input.productId ? { product_id: input.productId } : {}),
    };
    this.queue.push(envelope);
    this.persist();
    this.scheduleFlush(this.queue.length >= MAX_BATCH_SIZE ? 0 : FLUSH_DELAY_MS);
    return envelope;
  }

  flush(): Promise<void> {
    if (this.paused) return Promise.resolve();
    if (this.inFlight) return this.inFlight;
    if (this.queue.length === 0) return Promise.resolve();
    if (this.timer !== null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
    const batch = this.queue.slice(0, MAX_BATCH_SIZE);
    const ids = new Set(batch.map((event) => event.event_id));
    this.inFlight = this.postEvents(batch)
      .then(() => {
        this.queue = this.queue.filter((event) => !ids.has(event.event_id));
        this.retryCount = 0;
        this.persist();
        this.listeners.forEach((listener) => listener(batch));
        if (this.queue.length > 0) this.scheduleFlush(FLUSH_DELAY_MS);
      })
      .catch(() => {
        this.retryCount += 1;
        const delay = Math.min(
          FLUSH_DELAY_MS * (2 ** (this.retryCount - 1)),
          MAX_RETRY_DELAY_MS,
        );
        this.scheduleFlush(delay);
      })
      .finally(() => {
        this.inFlight = null;
      });
    return this.inFlight;
  }

  flushWithBeacon(): boolean {
    if (this.queue.length === 0 || typeof navigator === "undefined" || !navigator.sendBeacon) {
      return false;
    }
    const body = JSON.stringify({ events: this.queue.slice(0, MAX_BEACON_BATCH_SIZE) });
    return navigator.sendBeacon(
      apiUrl("/api/v1/events"),
      new Blob([body], { type: "application/json" }),
    );
  }

  pendingEvents(): readonly EventEnvelope[] {
    return this.queue;
  }

  resetForTests(): void {
    if (this.timer !== null && typeof window !== "undefined") window.clearTimeout(this.timer);
    this.timer = null;
    this.queue = [];
    this.sessionId = null;
    this.userId = undefined;
    this.retryCount = 0;
    this.paused = false;
    this.memorySequences.clear();
    this.persist();
  }

  private nextSequence(sessionId: string): number {
    const key = `${SEQUENCE_PREFIX}${sessionId}`;
    let current = this.memorySequences.get(sessionId) ?? 0;
    try {
      const stored = Number(this.sessionStorage?.getItem(key) ?? 0);
      if (Number.isSafeInteger(stored) && stored >= 0) current = Math.max(current, stored);
    } catch {
      // The in-memory counter remains monotonic when storage is blocked.
    }
    const next = current + 1;
    this.memorySequences.set(sessionId, next);
    try {
      this.sessionStorage?.setItem(key, String(next));
    } catch {
      // The in-memory counter remains authoritative for this page lifetime.
    }
    return next;
  }

  private persist(): void {
    try {
      this.localStorage?.setItem(BUFFER_KEY, JSON.stringify(this.queue));
    } catch {
      // A full/blocked storage area must never make the storefront unusable.
    }
  }

  private scheduleFlush(delay: number): void {
    if (typeof window === "undefined" || this.paused) return;
    if (this.timer !== null) {
      window.clearTimeout(this.timer);
    }
    this.timer = window.setTimeout(() => {
      this.timer = null;
      void this.flush();
    }, delay);
  }
}

export const eventClient = new EventClient();

export function emit<T extends EventType>(eventType: T, input: EventInput<T>): EventEnvelope | null {
  return eventClient.emit(eventType, input);
}
