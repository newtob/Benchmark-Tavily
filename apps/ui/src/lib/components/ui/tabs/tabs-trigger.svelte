<script lang="ts">
  import { cn } from "$lib/utils.js";
  import type { HTMLButtonAttributes } from "svelte/elements";
  import { getTabsContext } from "./context.js";

  let {
    value,
    class: className,
    children,
    ...restProps
  }: HTMLButtonAttributes & { value: string } = $props();

  const ctx = getTabsContext();
  const active = $derived(ctx.value === value);
</script>

<button
  type="button"
  role="tab"
  aria-selected={active}
  data-state={active ? "active" : "inactive"}
  onclick={() => ctx.setValue(value)}
  class={cn(
    "inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    active
      ? "bg-background text-foreground shadow-sm"
      : "text-muted-foreground hover:text-foreground",
    className,
  )}
  {...restProps}
>
  {@render children?.()}
</button>
