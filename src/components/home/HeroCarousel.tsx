import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { banners } from "../../data/banners";

const AUTO_ADVANCE_MS = 6000;

export function HeroCarousel() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const touchStart = useRef<number | null>(null);
  const go = useCallback((direction: 1 | -1) => {
    setIndex((current) => (current + direction + banners.length) % banners.length);
  }, []);

  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(() => go(1), AUTO_ADVANCE_MS);
    return () => window.clearInterval(timer);
  }, [go, paused]);

  return (
    <section
      className="group relative mb-3 overflow-hidden bg-white shadow-fk-card"
      aria-roledescription="carousel"
      aria-label="Featured offers"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
      onTouchStart={(event) => { touchStart.current = event.touches[0]?.clientX ?? null; setPaused(true); }}
      onTouchEnd={(event) => {
        const end = event.changedTouches[0]?.clientX;
        if (touchStart.current !== null && end !== undefined && Math.abs(end - touchStart.current) > 48) go(end < touchStart.current ? 1 : -1);
        touchStart.current = null;
        setPaused(false);
      }}
    >
      <div className="flex transition-transform duration-500 ease-out motion-reduce:transition-none" style={{ transform: `translateX(-${index * 100}%)` }}>
        {banners.map((banner, slideIndex) => (
          <article key={banner.id} aria-hidden={slideIndex !== index} className={`flex h-[220px] w-full shrink-0 flex-col justify-center bg-gradient-to-r px-7 sm:h-[280px] sm:px-16 ${banner.gradient}`}>
            <p className={`text-fk-md font-medium uppercase tracking-widest ${banner.accent}`}>Flipkart exclusive</p>
            <h2 className="mt-2 max-w-xl text-balance text-3xl font-bold leading-tight text-white sm:text-5xl">{banner.headline}</h2>
            <p className="mt-3 max-w-lg text-pretty text-fk-md text-white/85 sm:text-fk-lg">{banner.sub}</p>
            {banner.href.startsWith("http") ? (
              <a href={banner.href} target="_blank" rel="noreferrer" tabIndex={slideIndex === index ? 0 : -1} className="mt-5 inline-flex min-h-11 w-fit items-center rounded-[2px] bg-white px-5 text-fk-md font-medium uppercase text-fk-blue shadow-fk-card hover:bg-fk-bg">{banner.cta}</a>
            ) : (
              <Link to={banner.href} tabIndex={slideIndex === index ? 0 : -1} className="mt-5 inline-flex min-h-11 w-fit items-center rounded-[2px] bg-white px-5 text-fk-md font-medium uppercase text-fk-blue shadow-fk-card hover:bg-fk-bg">{banner.cta}</Link>
            )}
          </article>
        ))}
      </div>

      <button onClick={() => go(-1)} aria-label="Previous offer" className="absolute left-0 top-1/2 hidden h-20 w-11 -translate-y-1/2 items-center justify-center bg-white/90 text-fk-ink opacity-90 shadow-md hover:opacity-100 sm:flex"><ChevronLeft aria-hidden="true" className="h-6 w-6" /></button>
      <button onClick={() => go(1)} aria-label="Next offer" className="absolute right-0 top-1/2 hidden h-20 w-11 -translate-y-1/2 items-center justify-center bg-white/90 text-fk-ink opacity-90 shadow-md hover:opacity-100 sm:flex"><ChevronRight aria-hidden="true" className="h-6 w-6" /></button>
      <div className="absolute bottom-2 left-1/2 flex -translate-x-1/2 gap-1" role="tablist" aria-label="Choose offer">
        {banners.map((banner, slideIndex) => <button key={banner.id} onClick={() => setIndex(slideIndex)} role="tab" aria-label={`Show offer ${slideIndex + 1}: ${banner.headline}`} aria-selected={slideIndex === index} className="flex h-8 w-8 items-center justify-center"><span className={`h-1.5 rounded-full transition-[width,background-color] motion-reduce:transition-none ${slideIndex === index ? "w-5 bg-white" : "w-1.5 bg-white/50"}`} /></button>)}
      </div>
    </section>
  );
}
