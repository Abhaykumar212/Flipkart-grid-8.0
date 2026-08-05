// Snapshots `src/data/products.ts` to `backend/data/catalog_export.json`.
//
// The frontend catalog stays the one source of truth (see `ProductAvailability`'s
// docstring in backend/schemas.py for the existing rationale) — this is a
// build-time export for the two backend features that need product *features*
// server-side and have no other way to get them: the offline recommender
// trainer (ml/train_recommender.py) and the RAG retrieval index
// (backend/agents/retrieval.py). Regenerate after editing products.ts:
//
//   node scripts/export-catalog.mjs
//
// `products.ts` has no TypeScript-only syntax in the array literal itself
// (only the `import type` line and the `: Product[]` annotation on the
// export), so stripping those two lines turns it into plain JS we can eval
// directly — no bundler or ts-node needed.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const srcPath = join(root, "src", "data", "products.ts");
const outDir = join(root, "backend", "data");
const outPath = join(outDir, "catalog_export.json");

const fullSource = readFileSync(srcPath, "utf-8");
const start = fullSource.indexOf("export const products: Product[] = ");
const end = fullSource.indexOf("\nexport const productById");
if (start === -1 || end === -1) {
  throw new Error("export-catalog: couldn't locate the products array literal");
}
const arrayLiteral = fullSource
  .slice(start, end)
  .replace(/export const products: Product\[\] = /, "");
const source = `globalThis.__products = ${arrayLiteral}`;

// eslint-disable-next-line no-eval
(0, eval)(source);
const products = globalThis.__products;
if (!Array.isArray(products) || products.length === 0) {
  throw new Error("export-catalog: failed to extract products array");
}

mkdirSync(outDir, { recursive: true });
writeFileSync(outPath, JSON.stringify(products, null, 2), "utf-8");
console.log(`Exported ${products.length} products -> ${outPath}`);
