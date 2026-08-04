export interface BehaviorEvent {
  type: string;
  timestamp: number;
  data: Record<string, any>;
  duration_seconds?: number;
  page: string;
}

export class EventTimeline {
  private events: BehaviorEvent[] = [];
  private unsyncedStartIndex: number = 0;
  private sessionId: string;
  private syncTimer: number | null = null;
  private pageEnterTime: Record<string, number> = {};
  private sectionTimers: Map<string, number> = new Map();
  
  constructor() {
    this.sessionId = sessionStorage.getItem('fk-pipeline-session-id') || `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem('fk-pipeline-session-id', this.sessionId);
    
    this.startPeriodicSync();
    this.setupUnloadHandler();
    
    this.record('session_start', {
      userAgent: navigator.userAgent,
      screenWidth: window.innerWidth,
      screenHeight: window.innerHeight,
      isMobile: window.innerWidth < 768,
      timestamp_iso: new Date().toISOString(),
    });
  }
  
  private getCurrentPage(): string {
    return window.location.pathname;
  }
  
  record(type: string, data: Record<string, any> = {}, page?: string): void {
    const event: BehaviorEvent = {
      type,
      timestamp: Date.now(),
      data,
      page: page || this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  startTimer(sectionId: string): () => number {
    const startTime = Date.now();
    this.sectionTimers.set(sectionId, startTime);
    
    return () => {
      return this.stopTimer(sectionId);
    };
  }
  
  stopTimer(sectionId: string): number {
    const startTime = this.sectionTimers.get(sectionId);
    if (!startTime) return 0;
    
    this.sectionTimers.delete(sectionId);
    return (Date.now() - startTime) / 1000;
  }
  
  recordPageEnter(page: string): void {
    this.pageEnterTime[page] = Date.now();
    this.record('page_enter', {}, page);
  }
  
  recordPageLeave(page: string): void {
    const enterTime = this.pageEnterTime[page];
    const duration = enterTime ? (Date.now() - enterTime) / 1000 : 0;
    
    const event: BehaviorEvent = {
      type: 'page_leave',
      timestamp: Date.now(),
      data: {},
      duration_seconds: duration,
      page: page,
    };
    this.events.push(event);
  }
  
  recordSearch(query: string, resultCount: number): void {
    this.record('search', { query, resultCount });
  }
  
  recordSearchResultsView(query: string, duration: number, productsViewed: string[]): void {
    const event: BehaviorEvent = {
      type: 'search_results_view',
      timestamp: Date.now(),
      data: { query, productsViewed },
      duration_seconds: duration,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordProductView(productId: string, productName: string, price: number, category: string): void {
    this.record('product_view', { productId, productName, price, category });
  }
  
  recordDescriptionRead(productId: string, duration: number): void {
    const event: BehaviorEvent = {
      type: 'description_read',
      timestamp: Date.now(),
      data: { productId },
      duration_seconds: duration,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordReviewsRead(productId: string, duration: number, reviewsScrolled: number): void {
    const event: BehaviorEvent = {
      type: 'reviews_read',
      timestamp: Date.now(),
      data: { productId, reviewsScrolled },
      duration_seconds: duration,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordSpecsViewed(productId: string, duration: number): void {
    const event: BehaviorEvent = {
      type: 'specs_viewed',
      timestamp: Date.now(),
      data: { productId },
      duration_seconds: duration,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordComparisonStarted(productIds: string[], productNames: string[]): void {
    this.record('comparison_started', { productIds, productNames });
  }
  
  recordAddToCart(productId: string, productName: string, price: number, fromPage: string): void {
    this.record('add_to_cart', { productId, productName, price, fromPage });
  }
  
  recordRemoveFromCart(productId: string): void {
    this.record('remove_from_cart', { productId });
  }
  
  recordCartView(duration: number, itemCount: number, totalValue: number): void {
    const event: BehaviorEvent = {
      type: 'cart_view',
      timestamp: Date.now(),
      data: { itemCount, totalValue },
      duration_seconds: duration,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordCheckoutStarted(step: number): void {
    this.record('checkout_started', { step });
  }
  
  recordCheckoutAbandoned(step: number, timeSpent: number): void {
    const event: BehaviorEvent = {
      type: 'checkout_abandoned',
      timestamp: Date.now(),
      data: { step },
      duration_seconds: timeSpent,
      page: this.getCurrentPage(),
    };
    this.events.push(event);
  }
  
  recordWishlistAdd(productId: string, productName: string): void {
    this.record('wishlist_add', { productId, productName });
  }
  
  recordCouponAttempt(code: string, success: boolean): void {
    this.record('coupon_attempt', { code, success });
  }
  
  recordIdleDetected(duration: number, page: string): void {
    const event: BehaviorEvent = {
      type: 'idle_detected',
      timestamp: Date.now(),
      data: {},
      duration_seconds: duration,
      page: page,
    };
    this.events.push(event);
  }
  
  getEvents(): BehaviorEvent[] {
    return [...this.events];
  }
  
  getSessionId(): string {
    return this.sessionId;
  }
  
  async syncToBackend(): Promise<void> {
    const eventsToSync = this.events.slice(this.unsyncedStartIndex);
    if (eventsToSync.length === 0) return;

    try {
      const response = await fetch('http://localhost:8000/api/sync-timeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          events: eventsToSync,
          email: sessionStorage.getItem('fk-user-email') || null,
        }),
      });

      if (response.ok) {
        this.unsyncedStartIndex = this.events.length;
      }
    } catch (e) {
      console.error('Failed to sync events to backend:', e);
    }
  }
  
  async flush(converted: boolean): Promise<void> {
    try {
      await fetch('http://localhost:8000/api/session-end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          events: this.events,
          converted,
          email: sessionStorage.getItem('fk-user-email') || null,
        }),
      });
    } catch (e) {
      console.error('Failed to flush session end:', e);
    }
  }
  
  private setupUnloadHandler(): void {
    window.addEventListener('beforeunload', () => {
      const eventsToSync = this.events.slice(this.unsyncedStartIndex);
      if (eventsToSync.length > 0) {
        const payload = JSON.stringify({
          session_id: this.sessionId,
          events: eventsToSync,
          email: sessionStorage.getItem('fk-user-email') || null,
        });
        
        navigator.sendBeacon('http://localhost:8000/api/sync-timeline', payload);
      }
    });
  }
  
  private startPeriodicSync(): void {
    this.syncTimer = window.setInterval(() => {
      this.syncToBackend();
    }, 30000) as unknown as number;
  }

  stopPeriodicSync(): void {
    if (this.syncTimer !== null) {
      window.clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }
}

export const eventTimeline = new EventTimeline();
