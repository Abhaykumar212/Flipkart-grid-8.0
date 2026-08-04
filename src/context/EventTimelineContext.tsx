import React, { createContext, useContext, useEffect, useCallback, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { EventTimeline, eventTimeline } from '../lib/eventTimeline';

interface EventTimelineContextValue {
  timeline: EventTimeline;
  recordSearch: (query: string, resultCount: number) => void;
  recordProductView: (productId: string, productName: string, price: number, category: string) => void;
  recordDescriptionRead: (productId: string, duration: number) => void;
  recordReviewsRead: (productId: string, duration: number, reviewsScrolled: number) => void;
  recordAddToCart: (productId: string, productName: string, price: number, fromPage: string) => void;
  recordRemoveFromCart: (productId: string) => void;
  recordCheckoutStarted: (step: number) => void;
  recordCheckoutAbandoned: (step: number, timeSpent: number) => void;
  recordComparisonStarted: (productIds: string[], productNames: string[]) => void;
  startSectionTimer: (sectionId: string) => () => number;
}

const EventTimelineContext = createContext<EventTimelineContextValue | undefined>(undefined);

export const useEventTimeline = () => {
  const context = useContext(EventTimelineContext);
  if (!context) {
    throw new Error('useEventTimeline must be used within an EventTimelineProvider');
  }
  return context;
};

interface EventTimelineProviderProps {
  children: ReactNode;
}

export const EventTimelineProvider: React.FC<EventTimelineProviderProps> = ({ children }) => {
  const location = useLocation();

  useEffect(() => {
    // Record page enter on location change
    eventTimeline.recordPageEnter(location.pathname);

    return () => {
      // Record page leave on unmount or route change
      eventTimeline.recordPageLeave(location.pathname);
    };
  }, [location.pathname]);

  const recordSearch = useCallback((query: string, resultCount: number) => {
    eventTimeline.recordSearch(query, resultCount);
  }, []);

  const recordProductView = useCallback((productId: string, productName: string, price: number, category: string) => {
    eventTimeline.recordProductView(productId, productName, price, category);
  }, []);

  const recordDescriptionRead = useCallback((productId: string, duration: number) => {
    eventTimeline.recordDescriptionRead(productId, duration);
  }, []);

  const recordReviewsRead = useCallback((productId: string, duration: number, reviewsScrolled: number) => {
    eventTimeline.recordReviewsRead(productId, duration, reviewsScrolled);
  }, []);

  const recordAddToCart = useCallback((productId: string, productName: string, price: number, fromPage: string) => {
    eventTimeline.recordAddToCart(productId, productName, price, fromPage);
  }, []);

  const recordRemoveFromCart = useCallback((productId: string) => {
    eventTimeline.recordRemoveFromCart(productId);
  }, []);

  const recordCheckoutStarted = useCallback((step: number) => {
    eventTimeline.recordCheckoutStarted(step);
  }, []);

  const recordCheckoutAbandoned = useCallback((step: number, timeSpent: number) => {
    eventTimeline.recordCheckoutAbandoned(step, timeSpent);
  }, []);

  const recordComparisonStarted = useCallback((productIds: string[], productNames: string[]) => {
    eventTimeline.recordComparisonStarted(productIds, productNames);
  }, []);

  const startSectionTimer = useCallback((sectionId: string) => {
    return eventTimeline.startTimer(sectionId);
  }, []);

  const value: EventTimelineContextValue = {
    timeline: eventTimeline,
    recordSearch,
    recordProductView,
    recordDescriptionRead,
    recordReviewsRead,
    recordAddToCart,
    recordRemoveFromCart,
    recordCheckoutStarted,
    recordCheckoutAbandoned,
    recordComparisonStarted,
    startSectionTimer,
  };

  return (
    <EventTimelineContext.Provider value={value}>
      {children}
    </EventTimelineContext.Provider>
  );
};
