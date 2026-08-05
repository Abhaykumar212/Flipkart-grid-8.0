import { Globe } from "lucide-react";
import { SUPPORTED_LANGUAGES, useLanguage } from "../../context/LanguageContext";

/** Small globe selector in the Navbar — drives the multilingual intervention system. */
export function LanguageSwitcher() {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex shrink-0 items-center gap-1 text-white" title="Intervention language">
      <Globe className="h-4 w-4" strokeWidth={2} />
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value as typeof language)}
        data-testid="language-switcher"
        aria-label="Intervention language"
        className="h-8 cursor-pointer rounded-[2px] border-none bg-transparent text-fk-sm font-medium text-white outline-none [&>option]:text-fk-ink"
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nativeLabel}
          </option>
        ))}
      </select>
    </div>
  );
}
