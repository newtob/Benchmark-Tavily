<script lang="ts">
  import { cn } from '$lib/utils';
  import type { Snippet } from 'svelte';
  import type { HTMLAttributes } from 'svelte/elements';

  interface Props extends HTMLAttributes<HTMLSpanElement> {
    class?: string;
    children?: Snippet;
  }

  let { class: className, children, ...rest }: Props = $props();
</script>

<span
  class={cn(
    'inline-flex items-center rounded px-1.5 py-0.5 text-xs font-bold',
    className,
  )}
  {...rest}
>
  {@render children?.()}
</span>
