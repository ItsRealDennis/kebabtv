// MapLibre's worker imports ./maplibre-gl-shared.mjs, so both files must be served side by side.
import { cpSync, mkdirSync } from "node:fs";
mkdirSync("public/maplibre", { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  cpSync(`node_modules/maplibre-gl/dist/${f}`, `public/maplibre/${f}`);
}
