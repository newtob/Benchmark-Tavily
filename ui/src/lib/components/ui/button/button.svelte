<script lang="ts">
  import { cn } from '$lib/utils';
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    class?: string;
    children?: Snippet;
  }

  let { class: className, children, ...rest }: Props = $props();
</script>

<button
  class={cn(
    'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50',
    className,
  )}
  {...rest}
>
  {@render children?.()}
</button>
