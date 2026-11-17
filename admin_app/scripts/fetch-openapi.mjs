/**
 * Refresh openapi.json from a running core_backend.
 *
 *   pnpm api:spec                                   # http://localhost:8000
 *   OPENAPI_URL=http://host:8000/openapi.json pnpm api:spec
 *
 * Without a running backend, export it straight from the code instead:
 *   cd ../core_backend && uv run python -c \
 *     "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" \
 *     > ../admin_app/openapi.json
 *
 * Then run `pnpm api:generate`.
 */
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";

const url = process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";
const response = await fetch(url);
if (!response.ok) {
  console.error(`Could not fetch ${url}: HTTP ${response.status}`);
  process.exit(1);
}
const spec = await response.json();
// Pretty-printed so spec changes are readable in diffs.
writeFileSync(
  resolve(import.meta.dirname, "..", "openapi.json"),
  JSON.stringify(spec, null, 2) + "\n",
);
console.log(`Saved openapi.json from ${url}`);
