import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const html = await readFile("dist/index.html", "utf8");
const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^\"]+)"/g)].map(
  (m) => m[1],
);
const hash = createHash("sha256").update(html).digest("hex").slice(0, 12);
let sw = await readFile("dist/sw.js", "utf8");
sw = sw
  .replace(
    /const BUILD_ASSETS\s*=\s*\[\];/,
    `const BUILD_ASSETS = ${JSON.stringify(assets)};`,
  )
  .replace("mikuy-shell-v1", "mikuy-shell-" + hash);
if (assets.length < 2 || !sw.includes(assets[0]))
  throw new Error("Precache PWA incompleto");
await writeFile("dist/sw.js", sw);
console.log(`PWA: ${assets.length} hashed assets precached; shell ${hash}.`);
