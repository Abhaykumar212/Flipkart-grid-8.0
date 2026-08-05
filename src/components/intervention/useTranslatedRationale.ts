import { useEffect, useState } from "react";
import type { Language } from "../../context/LanguageContext";
import { fallbackRationale } from "../../lib/interventionTranslations";

/**
 * Translates the one piece of intervention text that's often LLM-personalised
 * per session (`rationale`) and so can't come from the static dictionary in
 * `interventionTranslations.ts`. Calls `POST /api/translate-intervention`
 * (backend/translate.py — Groq, best-effort, cached server-side) once per
 * distinct (text, language) pair and never blocks the card on it: the English
 * text is swapped for the lever's static fallback sentence immediately, then
 * for the exact translation if/when it arrives.
 */
const cache = new Map<string, string>();

export function useTranslatedRationale(leverId: string, englishRationale: string, language: Language): string {
  const cacheKey = `${language}::${englishRationale}`;
  const [translated, setTranslated] = useState<string | null>(() => cache.get(cacheKey) ?? null);

  useEffect(() => {
    if (language === "en") return;
    const cached = cache.get(cacheKey);
    if (cached) {
      setTranslated(cached);
      return;
    }
    let cancelled = false;
    fetch("http://localhost:8000/api/translate-intervention", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: englishRationale, target_lang: language }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (cancelled || !data.translated) return;
        cache.set(cacheKey, data.translated);
        setTranslated(data.translated);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cacheKey, language]);

  if (language === "en") return englishRationale;
  return translated ?? fallbackRationale(leverId, language) ?? englishRationale;
}
