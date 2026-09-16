<script lang="ts">
  interface Props {
    activeTab: 'summary' | 'searches';
    onChange: (tab: 'summary' | 'searches') => void;
  }

  let { activeTab, onChange }: Props = $props();

  const tabs = [
    { id: 'summary', label: 'Summary', testId: 'tab-summary' },
    { id: 'searches', label: 'Searches', testId: 'tab-searches' },
  ] as const;
</script>

<div role="tablist" class="inline-flex items-center gap-1 bg-surface-2 rounded-md p-1">
  {#each tabs as tab}
    <button
      type="button"
      role="tab"
      aria-selected={activeTab === tab.id}
      data-state={activeTab === tab.id ? 'active' : 'inactive'}
      class={`px-[18px] py-2 rounded text-sm font-semibold transition-all ${
        activeTab === tab.id
          ? 'bg-surface text-fg1 shadow-[0_1px_3px_rgba(0,37,53,.1)]'
          : 'bg-transparent text-fg3 hover:text-fg1'
      }`}
      onclick={() => onChange(tab.id)}
      data-testid={tab.testId}
    >
      {tab.label}
    </button>
  {/each}
</div>
