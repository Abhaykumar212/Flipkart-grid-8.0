import { Fragment } from "react";

/** `**bold**` → <strong>, everything else passes through untouched. */
function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${i}`} className="font-semibold">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={`${keyPrefix}-${i}`}>{part}</Fragment>
    ),
  );
}

/**
 * Minimal markdown-lite for LLM output: `- ` / `* ` / `1. ` lines become a
 * real bullet or numbered list, `**bold**` becomes real bold, blank lines
 * separate paragraphs. Everything else renders as plain text. Deliberately
 * not a full markdown parser — LLM prompts here are instructed to use only
 * this small subset, so this only needs to cover what they actually produce.
 */
export function FormattedText({ text, className = "" }: { text: string; className?: string }) {
  const lines = text.split("\n");
  const blocks: Array<{ type: "ul" | "ol" | "p"; items: string[] }> = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    const bulletMatch = /^[-*•]\s+(.*)/.exec(line);
    const numberedMatch = /^\d+[.)]\s+(.*)/.exec(line);
    const kind: "ul" | "ol" | "p" = bulletMatch ? "ul" : numberedMatch ? "ol" : "p";
    const content = bulletMatch?.[1] ?? numberedMatch?.[1] ?? line;

    const last = blocks[blocks.length - 1];
    if (last && last.type === kind && kind !== "p") {
      last.items.push(content);
    } else {
      blocks.push({ type: kind, items: [content] });
    }
  }

  if (blocks.length === 0) return null;

  return (
    <div className={className}>
      {blocks.map((block, i) => {
        if (block.type === "p") {
          return (
            <p key={i} className={i > 0 ? "mt-1.5" : undefined}>
              {renderInline(block.items[0], `p-${i}`)}
            </p>
          );
        }
        const Tag = block.type;
        return (
          <Tag key={i} className={`${i > 0 ? "mt-1.5" : ""} flex flex-col gap-1 ${block.type === "ul" ? "list-none" : "list-decimal pl-4"}`}>
            {block.items.map((item, j) => (
              <li key={j} className={block.type === "ul" ? "flex items-start gap-1.5" : undefined}>
                {block.type === "ul" && <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-current opacity-60" />}
                <span>{renderInline(item, `li-${i}-${j}`)}</span>
              </li>
            ))}
          </Tag>
        );
      })}
    </div>
  );
}
