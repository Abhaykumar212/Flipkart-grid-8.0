import { Link } from "react-router-dom";
import { Store, Gift, HelpCircle, TrendingUp } from "lucide-react";
import {
  FacebookIcon,
  TwitterIcon,
  YoutubeIcon,
  InstagramIcon,
} from "../ui/SocialIcons";
import { catalogCategories } from "../../data/categories";

const columns: { title: string; links: string[] }[] = [
  {
    title: "About",
    links: ["Contact Us", "About Us", "Careers", "Flipkart Stories", "Press", "Corporate Information"],
  },
  {
    title: "Group Companies",
    links: ["Myntra", "Cleartrip", "Shopsy"],
  },
  {
    title: "Help",
    links: ["Payments", "Shipping", "Cancellation & Returns", "FAQ"],
  },
  {
    title: "Consumer Policy",
    links: [
      "Cancellation & Returns",
      "Terms Of Use",
      "Security",
      "Privacy",
      "Sitemap",
      "Grievance Redressal",
      "EPR Compliance",
    ],
  },
];

const socials = [
  { label: "Facebook", icon: FacebookIcon, href: "https://www.facebook.com/flipkart" },
  { label: "Twitter", icon: TwitterIcon, href: "https://x.com/flipkart" },
  { label: "YouTube", icon: YoutubeIcon, href: "https://www.youtube.com/flipkart" },
  { label: "Instagram", icon: InstagramIcon, href: "https://www.instagram.com/flipkart" },
];

const bottomLinks = [
  { label: "Become a Seller", icon: Store, href: "https://seller.flipkart.com" },
  { label: "Advertise", icon: TrendingUp, href: "https://advertising.flipkart.com" },
  { label: "Gift Cards", icon: Gift, href: "https://www.flipkart.com/account/giftcard" },
  { label: "Help Center", icon: HelpCircle, href: "https://www.flipkart.com/helpcentre" },
];

const informationalHref = (label: string) => {
  if (label === "Careers") return "https://www.flipkartcareers.com";
  if (label === "Myntra") return "https://www.myntra.com";
  if (label === "Cleartrip") return "https://www.cleartrip.com";
  if (label === "Shopsy") return "https://www.shopsy.in";
  return "https://www.flipkart.com/helpcentre";
};

export function Footer() {
  return (
    <footer className="mt-6 bg-fk-footer text-white">
      <div className="mx-auto max-w-fk px-4 py-10">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4 lg:grid-cols-8">
          <nav aria-label="Shop categories">
            <h3 className="mb-3 text-fk-sm uppercase tracking-wide text-fk-footer-ink">Shop</h3>
            <ul className="space-y-1">
              {catalogCategories.map((category) => <li key={category.slug}><Link to={`/category/${category.slug}`} className="inline-flex min-h-11 items-center text-fk-base text-white/90 hover:underline md:min-h-8">{category.shortLabel}</Link></li>)}
            </ul>
          </nav>
          {columns.map((col) => (
            <div key={col.title}>
              <h3 className="mb-3 text-fk-sm uppercase tracking-wide text-fk-footer-ink">
                {col.title}
              </h3>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href={informationalHref(link)} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center text-fk-base text-white/90 hover:underline md:min-h-8">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div>
            <h3 className="mb-3 text-fk-sm uppercase tracking-wide text-fk-footer-ink">
              Social
            </h3>
            <ul className="space-y-2">
              {socials.map(({ label, icon: Icon, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="flex min-h-11 items-center gap-2 text-fk-base text-white/90 hover:underline md:min-h-8"
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Address block — separated by a hairline like the real footer */}
          <div className="col-span-2 grid min-w-0 grid-cols-1 gap-8 border-white/15 sm:grid-cols-2 lg:border-l lg:pl-8">
            <div className="min-w-0">
              <h3 className="mb-3 text-fk-sm uppercase tracking-wide text-fk-footer-ink">
                Mail Us:
              </h3>
              <address className="text-fk-base not-italic leading-5 break-words text-white/90">
                Flipkart Internet Private Limited,
                <br />
                Buildings Alyssa, Begonia &amp;
                <br />
                Clove Embassy Tech Village,
                <br />
                Outer Ring Road, Devarabeesanahalli Village,
                <br />
                Bengaluru, 560103,
                <br />
                Karnataka, India
              </address>
            </div>
            <div className="min-w-0">
              <h3 className="mb-3 text-fk-sm uppercase tracking-wide text-fk-footer-ink">
                Registered Office Address:
              </h3>
              <address className="text-fk-base not-italic leading-5 break-words text-white/90">
                Flipkart Internet Private Limited,
                <br />
                Buildings Alyssa, Begonia &amp;
                <br />
                Clove Embassy Tech Village,
                <br />
                Outer Ring Road, Devarabeesanahalli Village,
                <br />
                Bengaluru, 560103,
                <br />
                Karnataka, India
                <br />
                CIN : U51109KA2012PTC066107
                <br />
                Telephone:{" "}
                <span className="text-fk-blue">044-45614700</span>
              </address>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-white/15">
        <div className="mx-auto flex max-w-fk flex-wrap items-center gap-x-8 gap-y-3 px-4 py-5 text-fk-base">
          {bottomLinks.map(({ label, icon: Icon, href }) => (
            <a key={label} href={href} target="_blank" rel="noreferrer" className="flex min-h-11 items-center gap-1.5 text-white/90">
              <Icon className="h-3.5 w-3.5 text-fk-yellow" strokeWidth={2} />
              {label}
            </a>
          ))}
          <span className="ml-auto text-white/90">&copy; 2007-2026 Flipkart.com</span>
        </div>
      </div>
    </footer>
  );
}
