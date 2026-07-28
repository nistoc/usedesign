/**
 * Copy the published schemas next to the compiled code so that a published package validates
 * against the same files the repository does. Run as part of `npm run build`.
 */
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const from = join(here, "..", "..", "..", "schema");
const to = join(here, "..", "dist", "schema");

mkdirSync(to, { recursive: true });
cpSync(from, to, { recursive: true });
console.log(`schema → ${to}`);
