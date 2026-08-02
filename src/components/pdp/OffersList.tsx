import { useState } from "react";
import { Landmark, Wallet, Repeat, Gift, Tag, ChevronDown, type LucideIcon } from "lucide-react";
import type { Emi } from "../../types/product";
import { formatINR } from "../../lib/format";

type OfferType = "bank" | "emi" | "exchange" | "combo" | "special";

interface OfferRow {
  type: OfferType;
  text: string;
}

const OFFER_META: Record<OfferType, { label: string; icon: LucideIcon; terms: string }> = {
  bank: {
    label: "Bank Offer",
    icon: Landmark,
    terms:
      "Offer valid on select bank credit/debit cards. Discount applied instantly at checkout. Not combinable with other bank offers. Valid while stocks last.",
  },
  emi: {
    label: "No Cost EMI",
    icon: Wallet,
    terms:
      "No Cost EMI is calculated after applying a discount equivalent to the standard EMI interest. Available on select banks and cards, subject to a minimum order value.",
  },
  exchange: {
    label: "Exchange Offer",
    icon: Repeat,
    terms:
      "Exchange value depends on the condition, model, and functionality of your old device, as assessed at the time of delivery. Final value may vary from the estimate shown here.",
  },
  combo: {
    label: "Partner Offer",
    icon: Gift,
    terms:
      "Applicable when the specified quantity or combination of items is added to cart. Discount is applied automatically at checkout — no coupon code needed.",
  },
  special: {
    label: "Special Price",
    icon: Tag,
    terms:
      "Price shown is inclusive of all applicable discounts. Valid for a limited time or while stocks last.",
  },
};

function classify(text: string): OfferType {
  const lower = text.toLowerCase();
  if (/(bank|hdfc|icici|\bsbi\b|axis|federal|bajaj|credit card|debit card)/.test(lower)) return "bank";
  if (/\bemi\b/.test(lower)) return "emi";
  if (/exchange/.test(lower)) return "exchange";
  if (/(buy \d|buy more|combo)/.test(lower)) return "combo";
  return "special";
}

/**
 * Merges the product's authored `offers` strings with a couple of synthesized
 * rows (EMI, and a fallback bank offer) so every product's PDP shows a
 * realistic, non-empty offers block — matching Flipkart's real PDP, which
 * essentially always surfaces at least a bank offer and an EMI line.
 */
function buildOfferRows(offers: string[], emi: Emi | undefined): OfferRow[] {
  const rows: OfferRow[] = offers.map((text) => ({ type: classify(text), text }));

  if (emi && !rows.some((r) => r.type === "emi")) {
    rows.push({
      type: "emi",
      text: `No Cost EMI starting ${formatINR(emi.monthly)}/month for ${emi.months} months`,
    });
  }

  if (rows.length === 0) {
    rows.push({
      type: "bank",
      text: "Bank Offer 5% Unlimited Cashback on Flipkart Axis Bank Credit Card",
    });
  }

  return rows;
}

interface OffersListProps {
  offers: string[];
  emi?: Emi;
}

export function OffersList({ offers, emi }: OffersListProps) {
  const rows = buildOfferRows(offers, emi);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div>
      <h2 className="text-fk-md font-medium text-fk-ink">Available offers</h2>
      <ul className="mt-2 flex flex-col divide-y divide-fk-border">
        {rows.map((row, i) => {
          const meta = OFFER_META[row.type];
          const Icon = meta.icon;
          const isOpen = openIndex === i;

          return (
            <li key={i} className="py-2.5 first:pt-0">
              <div className="flex items-start gap-2 text-fk-base text-fk-ink">
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-fk-green" strokeWidth={2} />
                <span className="flex-1">
                  <span className="font-medium">{meta.label}</span> {row.text}{" "}
                  <button
                    onClick={() => setOpenIndex(isOpen ? null : i)}
                    className="inline-flex items-center gap-0.5 font-medium text-fk-blue"
                  >
                    T&amp;C
                    <ChevronDown
                      className={`h-3 w-3 transition-transform ${isOpen ? "rotate-180" : ""}`}
                      strokeWidth={2.5}
                    />
                  </button>
                </span>
              </div>
              {isOpen && (
                <p className="mt-1.5 pl-6 text-fk-sm text-fk-muted">{meta.terms}</p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
