import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { eventClient } from "../lib/events";

afterEach(() => {
  cleanup();
  eventClient.resetForTests();
  localStorage.clear();
  sessionStorage.clear();
  vi.restoreAllMocks();
});
