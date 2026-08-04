import { useCallback, useEffect, useRef, useState } from "react";
import {
  describeSpeechError,
  getSpeechRecognitionCtor,
  SPEECH_RECOGNITION_LANG,
  type SpeechRecognitionInstance,
} from "../lib/speech";

export type SpeechRecognitionStatus = "idle" | "listening" | "processing" | "error";

interface UseSpeechRecognitionOptions {
  /** Called once per utterance with the final recognized text — never partial. */
  onResult: (transcript: string) => void;
}

interface UseSpeechRecognitionReturn {
  status: SpeechRecognitionStatus;
  /** False when the browser has no SpeechRecognition implementation at all. */
  isSupported: boolean;
  errorMessage: string | null;
  /** Live partial transcript while listening — optional, for a "hearing you" indicator. */
  interimTranscript: string;
  start: () => void;
  stop: () => void;
}

const ERROR_DISPLAY_MS = 3000;

/**
 * Wraps the native Web Speech API as a small state machine: idle → listening
 * → processing → idle (or → error → idle). Auto-stops on silence — the
 * browser's own end-of-speech detection does that (continuous=false) — so
 * there is no manual "stop recording" step in the happy path.
 *
 * Deliberately does nothing else: no submission, no backend calls, no product
 * logic. `onResult` is the only way this hook talks to the outside world, and
 * the caller decides what "submit exactly like typed input" means.
 */
export function useSpeechRecognition({ onResult }: UseSpeechRecognitionOptions): UseSpeechRecognitionReturn {
  const isSupported = getSpeechRecognitionCtor() !== null;

  const [status, setStatus] = useState<SpeechRecognitionStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const onResultRef = useRef(onResult);
  const errorTimeoutRef = useRef<number | null>(null);

  // Keeps `start` stable across renders without going stale on the callback.
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  const detachHandlers = useCallback((recognition: SpeechRecognitionInstance) => {
    recognition.onstart = null;
    recognition.onresult = null;
    recognition.onerror = null;
    recognition.onend = null;
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setStatus("error");
      setErrorMessage("Voice input is not supported in this browser.");
      return;
    }

    // A fresh instance per utterance avoids vendor quirks around restarting a
    // previously-stopped recognizer.
    if (recognitionRef.current) {
      detachHandlers(recognitionRef.current);
      recognitionRef.current.abort();
    }
    if (errorTimeoutRef.current !== null) {
      window.clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = null;
    }

    const recognition = new Ctor();
    recognition.lang = SPEECH_RECOGNITION_LANG;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    setErrorMessage(null);
    setInterimTranscript("");

    recognition.onstart = () => setStatus("listening");

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) finalTranscript += result[0].transcript;
        else interim += result[0].transcript;
      }

      if (finalTranscript.trim()) {
        setStatus("processing");
        setInterimTranscript("");
        onResultRef.current(finalTranscript.trim());
      } else {
        setInterimTranscript(interim);
      }
    };

    recognition.onerror = (event) => {
      // Firing on our own start()-triggered abort() isn't a real failure.
      if (event.error === "aborted") return;
      setStatus("error");
      setErrorMessage(describeSpeechError(event.error));
      errorTimeoutRef.current = window.setTimeout(() => {
        setStatus("idle");
        setErrorMessage(null);
      }, ERROR_DISPLAY_MS);
    };

    recognition.onend = () => {
      detachHandlers(recognition);
      recognitionRef.current = null;
      setInterimTranscript("");
      // Let the error state finish its own timed display instead of
      // snapping back to idle the instant the recognizer session closes.
      setStatus((current) => (current === "error" ? current : "idle"));
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [detachHandlers]);

  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current !== null) window.clearTimeout(errorTimeoutRef.current);
      const recognition = recognitionRef.current;
      if (recognition) {
        detachHandlers(recognition);
        recognition.abort();
      }
    };
  }, [detachHandlers]);

  return { status, isSupported, errorMessage, interimTranscript, start, stop };
}
