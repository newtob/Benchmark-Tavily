<script lang="ts">
  import { cn } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";
  import { getTabsContext } from "./context.js";

  let {
    value,
    class: className,
    children,
    ...restProps
  }: HTMLAttributes<HTMLDivElement> & { value: string } = $props();

  const ctx = getTabsContext();
  const active = $derived(ctx.value === value);
</script>

{#if active}
  <div role="tabpanel" class={cn("outline-none", className)} {...restProps}>
    {@render children?.()}
  </div>
{/if}
