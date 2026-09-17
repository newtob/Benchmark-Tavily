<script lang="ts">
  import { Badge } from '$lib/components/ui/badge';
  import { Card } from '$lib/components/ui/card';
  import type { SearchQuery } from '$lib/models';

  interface Props {
    search: SearchQuery;
  }

  let { search }: Props = $props();
</script>

<Card class="p-6" data-testid="search-item">
  <p class="text-base font-semibold text-fg1 mb-1">{search.query}</p>
  <p class="text-sm text-fg3 mb-4">{search.note}</p>

  <div>
    <p class="text-xs font-medium text-fg2 mb-2">Success requires the response to include</p>
    <div class="flex flex-wrap gap-2">
      {#each search.successfuly_return_includes as term (term)}
        <Badge class="bg-surface-2 text-fg2 border border-border">{term}</Badge>
      {/each}
    </div>
  </div>
</Card>
