import { defineConfig } from "tsup";
import pkg from "./package.json" with { type: "json" };

export default defineConfig({
  entry: ["src/index.ts", "src/express.ts"],
  format: ["esm", "cjs"],
  dts: true,
  sourcemap: true,
  clean: true,
  splitting: false,
  bundle: true,
  platform: "node",
  // Single-sources the SDK version from package.json into the build instead
  // of a hand-maintained constant, which had drifted from the real version
  // (client.ts reported 0.1.0 in its User-Agent while package.json was
  // already at 0.1.1).
  define: {
    __APILENS_SDK_VERSION__: JSON.stringify(pkg.version),
  },
});
