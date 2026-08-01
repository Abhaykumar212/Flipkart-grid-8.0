import type { SpecSection } from "../../types/product";

interface SpecificationsTableProps {
  sections: SpecSection[];
}

export function SpecificationsTable({ sections }: SpecificationsTableProps) {
  return (
    <section className="rounded-[2px] bg-white p-4 sm:p-6">
      <h2 className="mb-4 text-fk-xl font-medium text-fk-ink">Specifications</h2>
      <div className="divide-y divide-fk-border">
        {sections.map((section) => (
          <div key={section.section} className="py-2">
            <div className="bg-fk-bg px-4 py-2 text-fk-md font-medium text-fk-ink">
              {section.section}
            </div>
            <table className="w-full">
              <tbody>
                {section.items.map((item) => (
                  <tr key={item.label} className="border-b border-fk-border last:border-0">
                    <td className="w-[38%] px-3 py-2.5 align-top text-fk-base text-fk-muted sm:px-4">
                      {item.label}
                    </td>
                    <td className="break-words px-3 py-2.5 text-fk-base text-fk-ink sm:px-4">{item.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </section>
  );
}
