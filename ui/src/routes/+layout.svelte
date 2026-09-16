<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();
</script>

<div class="min-h-screen flex flex-col bg-background">
  {@render children()}
</div>
