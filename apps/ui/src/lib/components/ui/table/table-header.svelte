<script lang="ts">
  import { cn } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: HTMLAttributes<HTMLTableSectionElement> & { ref?: HTMLTableSectionElement | null } =
    $props();
</script>

<thead bind:this={ref} class={cn("[&_tr]:border-b", className)} {...restProps}>
  {@render children?.()}
</thead>
