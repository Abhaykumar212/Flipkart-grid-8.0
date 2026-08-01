import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { banners } from "../../data/banners";

const AUTO_ADVANCE_MS = 5000;

export function HeroCarousel() {
  const [index, setIndex] = useState(0);

  const go = useCallback((dir: 1 | -1) => {
    setIndex((i) => (i + dir + banners.length) % banners.length);
  }, []);

  useEffect(() => {
    const id = setInterval(() => go(1), AUTO_ADVANCE_MS);
    return () => clearInterval(id);
  }, [go, index]);

  return (
    <section className="group relative mb-3 overflow-hidden bg-white shadow-fk-card">
      <div
        className="flex transition-transform duration-500 ease-out"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {banners.map((b) => (
          <div
            key={b.id}
            className={`flex h-[180px] w-full shrink-0 flex-col justify-center bg-gradient-to-r px-10 sm:h-[280px] sm:px-16 ${b.gradient}`}
          >
            <p className={`text-fk-md font-medium uppercase tracking-widest ${b.accent}`}>
              {b.cta}
            </p>
            <h2 className="mt-2 max-w-xl text-3xl font-bold leading-tight text-white sm:text-5xl">
              {b.headline}
            </h2>
            <p className="mt-3 max-w-lg text-fk-md text-white/85 sm:text-fk-lg">{b.sub}</p>
          </div>
        ))}
      </div>

      <button
        onClick={() => go(-1)}
        aria-label="Previous banner"
        className="absolute left-0 top-1/2 flex h-20 w-9 -translate-y-1/2 items-center justify-center bg-white/90 opacity-0 shadow-md transition-opacity group-hover:opacity-100"
      >
        <ChevronLeft className="h-6 w-6 text-fk-ink" />
      </button>
      <button
        onClick={() => go(1)}
        aria-label="Next banner"
        className="absolute right-0 top-1/2 flex h-20 w-9 -translate-y-1/2 items-center justify-center bg-white/90 opacity-0 shadow-md transition-opacity group-hover:opacity-100"
      >
        <ChevronRight className="h-6 w-6 text-fk-ink" />
      </button>

      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
        {banners.map((b, i) => (
          <button
            key={b.id}
            onClick={() => setIndex(i)}
            aria-label={`Go to banner ${i + 1}`}
            aria-current={i === index}
            className={`h-1.5 rounded-full transition-all ${
              i === index ? "w-5 bg-white" : "w-1.5 bg-white/50"
            }`}
          />
        ))}
      </div>
    </section>
  );
}
