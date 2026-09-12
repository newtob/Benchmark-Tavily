// Tightens built-in TypeScript types (JSON.parse, res.json(), .catch(e), etc.)
// so they resolve to `unknown` instead of `any`. Included automatically once
// referenced from tsconfig's `include` glob — no explicit import needed.
import "@total-typescript/ts-reset";
