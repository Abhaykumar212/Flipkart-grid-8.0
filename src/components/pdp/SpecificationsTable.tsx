import type { SpecSection } from "../../types/product";
import { useIntervention } from "../../context/InterventionContext";
import { rankSpecSectionsForDiagnosis } from "../../lib/adaptiveContent";
import { InlineHighlight } from "../intervention/InlineHighlight";

interface SpecificationsTableProps {
  productId: string;
  sections: SpecSection[];
}

export function SpecificationsTable({ productId, sections }: SpecificationsTableProps) {
  const { diagnosis } = useIntervention();
  // Passive content ordering only. This does not enter selectSurface or touch
  // the fatigue budget because it merely reorders content already on the page.
  const orderedSections = rankSpecSectionsForDiagnosis(
    sections,
    diagnosis?.productId === productId ? diagnosis.analysis : null,
  );

  // When the ranker promoted a section to the top, highlight that section
  // header with a quiet tint so there's a visual hint about why the order
  // changed. We detect this by checking whether the first section in the
  // reordered list differs from the original first section.
  const wasReordered =
    diagnosis &&
    sections.length >= 2 &&
    orderedSections.length >= 2 &&
    orderedSections[0].section !== sections[0].section;

  return (
    <section className="rounded-[2px] bg-white p-6">
      <h2 className="mb-4 text-fk-xl font-medium text-fk-ink">Specifications</h2>
      <div className="divide-y divide-fk-border">
        {orderedSections.map((section, index) => {
          const isPromoted = wasReordered && index === 0;
          const header = (
            <div className="bg-fk-bg px-4 py-2 text-fk-md font-medium text-fk-ink">
              {section.section}
            </div>
          );
          return (
            <div key={section.section} className="py-2">
              {isPromoted ? (
                <InlineHighlight variant="quiet" title="Relevant to your concern">
                  {header}
                </InlineHighlight>
              ) : (
                header
              )}
              <table className="w-full">
                <tbody>
                  {section.items.map((item) => (
                    <tr key={item.label} className="border-b border-fk-border last:border-0">
                      <td className="w-[38%] px-4 py-2.5 align-top text-fk-base text-fk-muted">
                        {item.label}
                      </td>
                      <td className="px-4 py-2.5 text-fk-base text-fk-ink">{item.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </section>
  );
}
