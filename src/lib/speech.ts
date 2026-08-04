/**
 * Thin wrapper around the browser's native Web Speech API. No network calls,
 * no external STT service — recognition happens entirely in the browser (or
 * the OS/browser vendor's own on-device or cloud engine, transparently to us).
 *
 * TypeScript's DOM lib doesn't ship types for this API (it's still
 * non-standard), so the minimal shape used here is hand-written rather than
 * pulling in a types-only dependency for a handful of fields.
 */

export interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: { transcript: string };
  length: number;
}

export interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}

export interface SpeechRecognitionErrorEventLike {
  error: string;
}

export interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

interface SpeechWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

/** Locale used for recognition — matches the storefront's own en-IN formatting elsewhere. */
export const SPEECH_RECOGNITION_LANG = "en-IN";

/** Returns the vendor-prefixed constructor if this browser supports it, else null. Never throws. */
export function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as SpeechWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getSpeechRecognitionCtor() !== null;
}

/** Maps the Web Speech API's terse error codes to copy a shopper would actually understand. */
export function describeSpeechError(errorCode: string): string {
  switch (errorCode) {
    case "not-allowed":
    case "permission-denied":
      return "Microphone permission was denied.";
    case "no-speech":
      return "Didn't catch that — try again.";
    case "audio-capture":
      return "No microphone was found.";
    case "network":
      return "Network issue — check your connection.";
    default:
      return "Voice input failed — try again.";
  }
}
