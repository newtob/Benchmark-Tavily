<script lang="ts">
  import { Badge } from '$lib/components/ui/badge';
  import type { BenchmarkGroup } from '$lib/models';

  interface Props {
    group: BenchmarkGroup;
    model: string;
  }

  let { group, model }: Props = $props();

  const methodLabels: Record<string, string> = {
    tavily_cli: 'Tavily CLI',
    tavily_mcp: 'Tavily MCP',
    search_in_prompt: 'Claude-web-search',
  };

  const winnerCost = $derived(group.items[group.winner_index]?.cost_usd ?? 0);

  function percentMore(cost: number): number {
    return winnerCost > 0 ? ((cost - winnerCost) / winnerCost) * 100 : 0;
  }
</script>

<div class="space-y-4" data-testid="comparison-group">
  <div class="mb-2">
    <h3 class="text-lg font-bold text-fg1">{group.title}</h3>
    <p class="text-sm text-fg3">{group.caption} &middot; Model: {model}</p>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    {#each group.items as item, index (item.method)}
      <div
        class={`relative rounded p-5 ${
          index === group.winner_index
            ? 'bg-surface border-l-4 border-l-syn-yellow shadow-[0_4px_16px_rgba(0,37,53,.12)] pt-[22px]'
            : 'bg-surface border border-border'
        }`}
        data-testid="benchmark-item"
      >
        {#if index === group.winner_index}
          <Badge
            data-testid="winner-badge"
            class="absolute -top-[11px] left-4 bg-syn-blue text-white text-[11px] uppercase tracking-[.04em] px-2.5 py-1 rounded-sm"
          >
            Most efficient
          </Badge>
        {/if}

        <div>
          <h4 class="text-base font-semibold text-fg1 mb-4">
            {methodLabels[item.method] ?? item.label}
          </h4>

          <div class="space-y-3">
            <div>
              <p class="text-xs text-fg3 mb-1">Total Cost</p>
              <p
                class={`text-2xl ${
                  index === group.winner_index ? 'font-extrabold text-fg2' : 'font-bold text-fg1'
                }`}
              >
                ${item.cost_usd.toFixed(4)}
              </p>
            </div>

            <div>
              <p class="text-xs text-fg3 mb-1">Tokens Used</p>
              <p class={`text-lg font-bold ${index === group.winner_index ? 'text-fg2' : 'text-fg1'}`}>
                {item.tokens.toLocaleString()}
              </p>
            </div>

            {#if index !== group.winner_index}
              <div>
                <p class="text-xs text-fg3 mb-1">% More Expensive</p>
                <p class="text-lg font-bold text-error" data-testid="percent-more">
                  +{percentMore(item.cost_usd).toFixed(0)}%
                </p>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>
