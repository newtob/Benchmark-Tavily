<script lang="ts">
  import { cn } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";

  let {
    class: className,
    children,
    ...restProps
  }: HTMLAttributes<HTMLDivElement> = $props();
</script>

<div
  role="tablist"
  class={cn(
    "inline-flex w-fit items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
    className,
  )}
  {...restProps}
>
  {@render children?.()}
</div>
