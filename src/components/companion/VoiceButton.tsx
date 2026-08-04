import { Loader2, Mic, MicOff } from "lucide-react";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";

interface VoiceButtonProps {
  /** Called with the final transcript — wire this to the same function typed submission uses. */
  onTranscript: (transcript: string) => void;
  /** Disabled while a message is already in flight, same as the text input/send button. */
  disabled?: boolean;
}

/**
 * A microphone button that plugs into the existing chat's send path — it
 * knows nothing about products, reviews, or the backend. Its entire
 * responsibility is: listen, convert speech to text, hand the text to
 * `onTranscript`, done. See `useSpeechRecognition` for the state machine.
 */
export function VoiceButton({ onTranscript, disabled }: VoiceButtonProps) {
  const { status, isSupported, errorMessage, interimTranscript, start, stop } = useSpeechRecognition({
    onResult: onTranscript,
  });

  if (!isSupported) {
    return (
      <button
        type="button"
        disabled
        title="Voice input is not supported in this browser."
        aria-label="Voice input is not supported in this browser"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200 text-slate-300"
      >
        <MicOff className="h-3.5 w-3.5" />
      </button>
    );
  }

  const label =
    status === "listening"
      ? "Listening — tap to stop"
      : status === "processing"
        ? "Processing speech"
        : status === "error"
          ? (errorMessage ?? "Voice input error")
          : "Start voice input";

  return (
    <div className="relative flex shrink-0 items-center">
      <button
        type="button"
        onClick={() => (status === "listening" ? stop() : start())}
        disabled={disabled || status === "processing"}
        aria-label={label}
        aria-pressed={status === "listening"}
        title={label}
        className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition disabled:opacity-40 ${
          status === "listening"
            ? "border-rose-200 bg-rose-50 text-rose-600"
            : status === "error"
              ? "border-amber-200 bg-amber-50 text-amber-600"
              : "border-slate-200 text-slate-500 hover:border-emerald-300 hover:text-emerald-600"
        }`}
      >
        {status === "listening" && (
          <span className="motion-reduce:hidden absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-300 opacity-50" />
        )}
        {status === "processing" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Mic className="relative h-3.5 w-3.5" />
        )}
      </button>

      {/* Screen-reader-only live status — the pulse/spinner communicate nothing on their own. */}
      <span role="status" aria-live="polite" className="sr-only">
        {status === "listening" && (interimTranscript ? `Listening: ${interimTranscript}` : "Listening…")}
        {status === "processing" && "Processing speech…"}
        {status === "error" && errorMessage}
      </span>
    </div>
  );
}
