// frontend/scripts/generate-icons.mjs
// One-shot resize: reads public/icon-1024.png and writes 5 derived PNGs.
// Run: pnpm gen:icons

import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(__dirname, "..", "public");
const source = path.join(publicDir, "icon-1024.png");

const SIZES = [180, 192, 256, 384, 512];

async function main() {
  try {
    await fs.access(source);
  } catch {
    console.error(
      `[gen:icons] source not found: ${source}\n` +
      `  Copy your square PNG to public/icon-1024.png and re-run.`
    );
    process.exit(1);
  }

  const meta = await sharp(source).metadata();
  if (meta.width !== meta.height) {
    console.error(
      `[gen:icons] source must be square, got ${meta.width}x${meta.height}`
    );
    process.exit(1);
  }
  if (meta.width < 512) {
    console.error(
      `[gen:icons] source must be at least 512x512, got ${meta.width}x${meta.height}`
    );
    process.exit(1);
  }

  await Promise.all(
    SIZES.map(async (size) => {
      const out = path.join(publicDir, `icon-${size}.png`);
      await sharp(source).resize(size, size, { fit: "cover" }).png().toFile(out);
      console.log(`[gen:icons] wrote ${out}`);
    })
  );

  console.log(`[gen:icons] done — ${SIZES.length} files written`);
}

main().catch((err) => {
  console.error("[gen:icons] failed:", err);
  process.exit(1);
});
