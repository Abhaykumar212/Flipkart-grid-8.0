import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { products } from "../src/data/products.ts";
import {
  getDescription,
  getRatingDistribution,
  getReviews,
  getSeller,
  getSpecifications,
} from "../src/lib/productDetails.ts";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = resolve(projectRoot, "fixtures", "catalog.json");

const catalog = products.map((product) => ({
  ...product,
  description: getDescription(product),
  seller: getSeller(product),
  specifications: getSpecifications(product),
  ratingDistribution: getRatingDistribution(product),
  reviews: getReviews(product),
}));

mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(catalog, null, 2)}\n`, "utf8");
console.log(`Exported ${catalog.length} products to ${outputPath}`);
