// Single static page: benchmark data is fetched client-side in +page.svelte
// (onMount), not via a load function, so prerendering just needs to emit
// the static shell. Required by adapter-static's `strict` mode.
export const prerender = true;
