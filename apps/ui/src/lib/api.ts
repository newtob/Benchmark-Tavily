/**
 * Typed client for GET /api/benchmark — a single shared client with a
 * stable relative base path, per this workspace's UI Behavior Contract
 * convention. Types mirror api/models/schemas.py; keep them in sync by
 * hand (no shared codegen in v1).
 */

export type BenchmarkCell = {
  tokens: number;
  price_usd: number;
  latency_ms: number;
  response_bytes: number;
  tokens_source: string;
};

export type WebContentRow = {
  url: string;
  claude_web_search: BenchmarkCell;
  tavily_extract: BenchmarkCell;
  tinyfish_fetch: BenchmarkCell;
};

export type BenchmarkResponse = {
  model: string;
  web_content_rows: WebContentRow[];
  generated_at: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchBenchmark(): Promise<BenchmarkResponse> {
  const response = await fetch("/api/benchmark");
  if (!response.ok) {
    throw new ApiError(
      `GET /api/benchmark failed: ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as BenchmarkResponse;
}
