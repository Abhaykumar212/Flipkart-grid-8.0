import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * Multilingual intervention system — the language a shopper wants their
 * intervention cards (and the companion's proactive offers) shown in.
 * Deliberately scoped to intervention content, not a full site translation:
 * see `src/lib/interventionTranslations.ts` for what actually reads this.
 */

export type Language = "en" | "hi" | "ta";

export const SUPPORTED_LANGUAGES: { code: Language; label: string; nativeLabel: string }[] = [
  { code: "en", label: "English", nativeLabel: "English" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी" },
  { code: "ta", label: "Tamil", nativeLabel: "தமிழ்" },
];

const STORAGE_KEY = "fk-lang-v1";

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

function readStoredLanguage(): Language {
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw === "hi" || raw === "ta" ? raw : "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => readStoredLanguage());

  const setLanguage = useCallback((lang: Language) => {
    localStorage.setItem(STORAGE_KEY, lang);
    setLanguageState(lang);
  }, []);

  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used within LanguageProvider");
  return context;
}
