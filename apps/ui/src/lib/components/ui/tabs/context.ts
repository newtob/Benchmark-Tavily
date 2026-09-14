import { getContext, setContext } from "svelte";

const KEY = Symbol("tabs");

export type TabsContext = {
  readonly value: string;
  setValue: (v: string) => void;
};

export function setTabsContext(ctx: TabsContext): void {
  setContext(KEY, ctx);
}

export function getTabsContext(): TabsContext {
  const ctx = getContext<TabsContext | undefined>(KEY);
  if (!ctx) {
    throw new Error("Tabs.Trigger/Tabs.Content must be used inside Tabs.Root");
  }
  return ctx;
}
