// frontend/widget/build.js
const esbuild = require("esbuild");
const watch = process.argv.includes("--watch");
esbuild.build({
  entryPoints: ["src/widget.js"],
  bundle: true,
  minify: !watch,
  outfile: "../../services/verification/static/widget.js",
  format: "iife",
}).catch(() => process.exit(1));
