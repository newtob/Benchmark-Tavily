<script lang="ts">
  import { cn } from "#lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";
  import { setTabsContext } from "./context.js";

  let {
    value = $bindable(),
    class: className,
    children,
    ...restProps
  }: HTMLAttributes<HTMLDivElement> & { value: string } = $props();

  setTabsContext({
    get value() {
      return value;
    },
    setValue(v: string) {
      value = v;
    },
  });
</script>

<div class={cn("flex flex-col gap-4", className)} {...restProps}>
  {@render children?.()}
</div>
