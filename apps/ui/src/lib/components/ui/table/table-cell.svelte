<script lang="ts">
  import { cn } from "#lib/utils.js";
  import type { HTMLTdAttributes } from "svelte/elements";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: HTMLTdAttributes & { ref?: HTMLTableCellElement | null } = $props();
</script>

<td
  bind:this={ref}
  class={cn("p-2 align-middle [&:has([role=checkbox])]:pr-0", className)}
  {...restProps}
>
  {@render children?.()}
</td>
