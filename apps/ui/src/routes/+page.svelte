<script lang="ts">
  import { onMount } from "svelte";
  import * as Table from "$lib/components/ui/table/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import { type BenchmarkCell, type BenchmarkResponse, fetchBenchmark } from "$lib/api.js";

  // Per this workspace's Svelte convention: anything assigned from an async
  // callback (onMount here) must be $state, not a plain `let` — a plain
  // `let` reassigned later doesn't trigger a re-render.
  let data = $state<BenchmarkResponse | null>(null);
  let error = $state<string | null>(null);
  let loading = $state(true);
  let activeTab = $state("summary");

  onMount(async () => {
    try {
      data = await fetchBenchmark();
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load benchmark data";
    } finally {
      loading = false;
    }
  });

  // The summary tab shows the average of all recorded searches, scaled up
  // by this factor purely so the displayed number reads as a bigger,
  // easier-to-parse figure ("what would 1000 of these cost") — this is a
  // display-only multiplication of one real search's averaged result, NOT
  // 1000 actual API/tool calls.
  const DISPLAY_SCALE = 1000;

  function average(cells: BenchmarkCell[]): { tokens: number; price_usd: number } {
    if (cells.length === 0) return { tokens: 0, price_usd: 0 };
    const tokens = cells.reduce((sum, c) => sum + c.tokens, 0) / cells.length;
    const price_usd = cells.reduce((sum, c) => sum + c.price_usd, 0) / cells.length;
    return { tokens, price_usd };
  }

  // Detail view: the real, unscaled per-search figures.
  function formatCell(tokens: number, priceUsd: number): string {
    return `${tokens} tok · $${priceUsd.toFixed(6)}`;
  }

  // Summary view: the same average, scaled for display (see DISPLAY_SCALE).
  function formatScaledAverage(avg: { tokens: number; price_usd: number }): string {
    const tokens = Math.round(avg.tokens * DISPLAY_SCALE);
    const price = avg.price_usd * DISPLAY_SCALE;
    return `${tokens.toLocaleString()} tok · $${price.toFixed(2)}`;
  }
</script>

<main class="mx-auto max-w-5xl p-8">
  <h1 class="text-2xl font-semibold">Tavily Benchmark</h1>
  <p class="mt-1 text-sm text-muted-foreground">
    Estimates the LLM token cost and price of running each method
    <strong>1000 searches</strong> — a single real search's result, averaged
    and scaled ×1000 for a more legible number (not 1000 actual API/tool
    calls). See specs/tavily-benchmark-app.md for methodology and its
    approximation caveats (tiktoken, not Anthropic's exact tokenizer; a
    fixed reference model's per-token rate, not each provider's own
    pricing).
  </p>

  {#if loading}
    <p class="mt-8 text-sm text-muted-foreground" data-testid="loading">Loading…</p>
  {:else if error}
    <p class="mt-8 text-sm text-destructive" data-testid="error">{error}</p>
  {:else if data}
    <Tabs.Root bind:value={activeTab} class="mt-8">
      <Tabs.List>
        <Tabs.Trigger value="summary" data-testid="tab-summary">Summary</Tabs.Trigger>
        <Tabs.Trigger value="searches" data-testid="tab-searches">Searches</Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="summary" data-testid="summary-panel">
        {@const toolCallRaw = average(data.tool_call_rows.map((r) => r.raw_tool_call))}
        {@const toolCallMcp = average(data.tool_call_rows.map((r) => r.mcp))}
        {@const webClaude = average(data.web_content_rows.map((r) => r.claude_web_search))}
        {@const webExtract = average(data.web_content_rows.map((r) => r.tavily_extract))}

        <section>
          <h2 class="text-lg font-medium">Tavily: Raw tool call vs MCP</h2>
          <p class="text-xs text-muted-foreground">
            Average across {data.tool_call_rows.length} searches, ×{DISPLAY_SCALE}.
          </p>
          <div class="mt-3 grid grid-cols-2 gap-4">
            <div class="rounded-lg border p-4" data-testid="summary-raw-tool-call">
              <div class="text-sm text-muted-foreground">Raw tool call</div>
              <div class="mt-1 text-xl font-semibold">{formatScaledAverage(toolCallRaw)}</div>
            </div>
            <div class="rounded-lg border p-4" data-testid="summary-mcp">
              <div class="text-sm text-muted-foreground">MCP</div>
              <div class="mt-1 text-xl font-semibold">{formatScaledAverage(toolCallMcp)}</div>
            </div>
          </div>
        </section>

        <section class="mt-8">
          <h2 class="text-lg font-medium">Web content: Claude Web Search vs Tavily Extract</h2>
          <p class="text-xs text-muted-foreground">
            Average across {data.web_content_rows.length} searches, ×{DISPLAY_SCALE}.
          </p>
          <div class="mt-3 grid grid-cols-2 gap-4">
            <div class="rounded-lg border p-4" data-testid="summary-claude-search">
              <div class="text-sm text-muted-foreground">Claude Web Search</div>
              <div class="mt-1 text-xl font-semibold">{formatScaledAverage(webClaude)}</div>
            </div>
            <div class="rounded-lg border p-4" data-testid="summary-tavily-extract">
              <div class="text-sm text-muted-foreground">Tavily Extract</div>
              <div class="mt-1 text-xl font-semibold">{formatScaledAverage(webExtract)}</div>
            </div>
          </div>
        </section>
      </Tabs.Content>

      <Tabs.Content value="searches" data-testid="searches-panel">
        <section>
          <h2 class="text-lg font-medium">Tavily: Raw tool call vs MCP</h2>
          {#if data.tool_call_rows.length === 0}
            <p class="mt-2 text-sm text-muted-foreground" data-testid="tool-call-empty">
              No data.
            </p>
          {:else}
            <Table.Root data-testid="tool-call-table">
              <Table.Header>
                <Table.Row>
                  <Table.Head>Query</Table.Head>
                  <Table.Head data-testid="col-raw">Raw tool call</Table.Head>
                  <Table.Head data-testid="col-mcp">MCP</Table.Head>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {#each data.tool_call_rows as row (row.query)}
                  <Table.Row data-testid="tool-call-row">
                    <Table.Cell>{row.query}</Table.Cell>
                    <Table.Cell>{formatCell(row.raw_tool_call.tokens, row.raw_tool_call.price_usd)}</Table.Cell>
                    <Table.Cell>{formatCell(row.mcp.tokens, row.mcp.price_usd)}</Table.Cell>
                  </Table.Row>
                {/each}
              </Table.Body>
            </Table.Root>
          {/if}
        </section>

        <section class="mt-10">
          <h2 class="text-lg font-medium">Web content: Claude Web Search vs Tavily Extract</h2>
          {#if data.web_content_rows.length === 0}
            <p class="mt-2 text-sm text-muted-foreground" data-testid="web-content-empty">
              No data.
            </p>
          {:else}
            <Table.Root data-testid="web-content-table">
              <Table.Header>
                <Table.Row>
                  <Table.Head>URL / Question</Table.Head>
                  <Table.Head data-testid="col-claude-search">Claude Web Search</Table.Head>
                  <Table.Head data-testid="col-tavily-extract">Tavily Extract</Table.Head>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {#each data.web_content_rows as row (row.url)}
                  <Table.Row data-testid="web-content-row">
                    <Table.Cell>
                      <div class="font-medium">{row.question}</div>
                      <div class="text-xs text-muted-foreground">{row.url}</div>
                    </Table.Cell>
                    <Table.Cell>
                      {formatCell(row.claude_web_search.tokens, row.claude_web_search.price_usd)}
                    </Table.Cell>
                    <Table.Cell>
                      {formatCell(row.tavily_extract.tokens, row.tavily_extract.price_usd)}
                    </Table.Cell>
                  </Table.Row>
                {/each}
              </Table.Body>
            </Table.Root>
          {/if}
        </section>
      </Tabs.Content>
    </Tabs.Root>
  {/if}
</main>
