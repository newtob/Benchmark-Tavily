import { z } from "zod";

/** API error wrapper carrying an HTTP status code. */
export class ApiError extends Error {
	constructor(
		message: string,
		public status: number,
	) {
		super(message);
		this.name = "ApiError";
	}
}

/** A single benchmark measurement for one search method. Mirrors api/models/schemas.py::BenchmarkItem. */
const BenchmarkItemSchema = z.object({
	label: z.string(),
	method: z.enum(["tavily_cli", "tavily_mcp", "search_in_prompt"]),
	tokens: z.number(),
	cost_usd: z.number(),
});

export type BenchmarkItem = z.infer<typeof BenchmarkItemSchema>;

/** A group of benchmark items with a designated winner. Mirrors BenchmarkGroup. */
const BenchmarkGroupSchema = z.object({
	title: z.string(),
	caption: z.string(),
	items: z.array(BenchmarkItemSchema),
	winner_index: z.number(),
});

export type BenchmarkGroup = z.infer<typeof BenchmarkGroupSchema>;

/** Complete benchmark response from GET /api/benchmark. Mirrors BenchmarkResponse. */
const BenchmarkResponseSchema = z.object({
	model: z.string(),
	groups: z.array(BenchmarkGroupSchema),
	generated_at: z.string(),
});

export type BenchmarkResponse = z.infer<typeof BenchmarkResponseSchema>;

/**
 * A fixed benchmark search query. Mirrors api/models/schemas.py::SearchQuery.
 * `successfuly_return_includes` is spelled exactly as the API returns it -
 * see searches.yaml's note on this key name; don't "fix" the typo here.
 */
const SearchQuerySchema = z.object({
	query: z.string(),
	note: z.string(),
	successfuly_return_includes: z.array(z.string()),
});

export type SearchQuery = z.infer<typeof SearchQuerySchema>;

export const schemas = {
	benchmarkItem: BenchmarkItemSchema,
	benchmarkGroup: BenchmarkGroupSchema,
	benchmarkResponse: BenchmarkResponseSchema,
	searchQuery: SearchQuerySchema,
	searches: z.array(SearchQuerySchema),
};

/** Anthropic models the UI lets the user pick between (must match api RATES keys). */
export const MODELS = [
	{ id: "claude-haiku-4-5", label: "Haiku 4.5" },
	{ id: "claude-sonnet-5", label: "Sonnet 5" },
	{ id: "claude-opus-5", label: "Opus 5" },
] as const;
