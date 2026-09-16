<script lang="ts">
  import { onMount } from 'svelte';
  import { Card } from '$lib/components/ui/card';
  import TabSwitcher from '$lib/components/TabSwitcher.svelte';
  import ComparisonGroup from '$lib/components/ComparisonGroup.svelte';
  import { fetchBenchmark, formatApiError } from '$lib/api-client';
  import { MODELS } from '$lib/models';
  import type { BenchmarkResponse } from '$lib/models';

  let activeTab = $state<'summary' | 'searches'>('summary');
  let selectedModel = $state<string>(MODELS[1].id); // default: Sonnet 5 (spec's primary reference model)
  let data = $state<BenchmarkResponse | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);

  async function loadBenchmark() {
    loading = true;
    error = null;
    data = null;

    try {
      data = await fetchBenchmark(selectedModel);
    } catch (err) {
      error = formatApiError(err);
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadBenchmark();
  });

  function handleModelChange(event: Event) {
    selectedModel = (event.target as HTMLSelectElement).value;
    loadBenchmark();
  }

  function handleTabChange(tab: 'summary' | 'searches') {
    activeTab = tab;
  }
</script>

<svelte:head>
  <title>Tavily Benchmark - Performance Comparison</title>
</svelte:head>

<div class="min-h-screen bg-background">
  <header class="bg-surface border-b border-border">
    <div class="max-w-6xl mx-auto px-4 py-8">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-4xl font-bold text-fg1 mb-2">Tavily Benchmark</h1>
          <p class="text-fg3">Performance comparison across search methods and models</p>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <label for="model-select" class="text-sm font-medium text-fg2">Model:</label>
        <select
          id="model-select"
          data-testid="model-selector"
          value={selectedModel}
          onchange={handleModelChange}
          class="px-3 py-2 border border-border rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-syn-blue-light focus:border-syn-blue-light"
        >
          {#each MODELS as model}
            <option value={model.id}>{model.label}</option>
          {/each}
        </select>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-4 py-12">
    <div class="mb-8">
      <TabSwitcher {activeTab} onChange={handleTabChange} />
    </div>

    {#if activeTab === 'summary'}
      <div class="space-y-8" data-testid="summary-panel">
        {#if loading}
          <div class="space-y-6">
            {#each [1, 2] as skeleton (skeleton)}
              <Card class="p-6">
                <div class="space-y-4">
                  <div class="h-6 bg-gray-200 rounded w-48 animate-pulse"></div>
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {#each [1, 2, 3] as col (col)}
                      <div class="space-y-3">
                        <div class="h-4 bg-gray-200 rounded w-32 animate-pulse"></div>
                        <div class="h-8 bg-gray-200 rounded w-20 animate-pulse"></div>
                        <div class="h-4 bg-gray-200 rounded animate-pulse"></div>
                      </div>
                    {/each}
                  </div>
                </div>
              </Card>
            {/each}
          </div>
        {:else if error}
          <Card class="p-6 border-red-200 bg-red-50">
            <div class="text-center">
              <h3 class="text-lg font-semibold text-red-900 mb-2">Failed to Load Benchmark Data</h3>
              <p class="text-red-700 text-sm mb-4">{error}</p>
              <button
                type="button"
                onclick={loadBenchmark}
                class="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </Card>
        {:else if data && data.groups.length > 0}
          {#each data.groups as group (group.title)}
            <ComparisonGroup {group} model={data.model} />
          {/each}
        {:else}
          <Card class="p-6 text-center">
            <p class="text-gray-600">No benchmark data available for the selected model.</p>
          </Card>
        {/if}
      </div>
    {/if}

    {#if activeTab === 'searches'}
      <div
        class="p-14 border border-dashed border-border rounded text-center"
        data-testid="searches-placeholder"
      >
        <p class="text-fg1 text-sm font-bold mb-2">Per-search detail</p>
        <p class="text-fg3 text-xs">Detailed search results coming soon</p>
      </div>
    {/if}

    <div class="mt-12 pt-6 border-t border-border">
      <p class="text-xs text-fg3 leading-relaxed">
        Benchmark results measure API call efficiency across three search methods: Tavily CLI (direct
        API call), Tavily MCP (Model Context Protocol integration), and Claude-web-search (Claude's
        native web search tool). Token counts use tiktoken as an approximation, not Anthropic's exact
        tokenizer; costs use a fixed reference model's per-token rate, not Tavily's own request pricing.
      </p>
    </div>
  </main>
</div>
