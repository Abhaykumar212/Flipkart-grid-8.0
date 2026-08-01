import { Link } from "react-router-dom";

/**
 * Flipkart wordmark recreated in markup — italic "Flipkart" with the
 * "Explore Plus" kicker and its yellow star underneath.
 */
export function Logo() {
  return (
    <Link to="/" className="shrink-0 leading-none" aria-label="Flipkart home">
      <span className="block text-fk-xl font-bold italic text-white">
        Flipkart
      </span>
      <span className="flex items-center gap-1 text-fk-xs italic text-white">
        Explore
        <span className="font-bold text-fk-yellow">Plus</span>
        <svg viewBox="0 0 24 24" className="h-2.5 w-2.5 fill-fk-yellow" aria-hidden="true">
          <path d="M12 2l2.4 7.2H22l-6.2 4.5 2.4 7.3L12 16.5l-6.2 4.5 2.4-7.3L2 9.2h7.6z" />
        </svg>
      </span>
    </Link>
  );
}
