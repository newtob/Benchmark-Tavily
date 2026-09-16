import { z } from "zod";
import { ApiError, type BenchmarkResponse, schemas } from "./models";

const API_BASE = "/api";

/**
 * Fetch benchmark results for a specific model
 * Uses Zod schema validation for type safety
 */
export async function fetchBenchmark(model: string): Promise<BenchmarkResponse> {
	try {
		const response = await fetch(`${API_BASE}/benchmark?model=${encodeURIComponent(model)}`);

		if (!response.ok) {
			throw new ApiError(`Failed to fetch benchmark data: ${response.statusText}`, response.status);
		}

		const data = await response.json();

		// Validate response matches BenchmarkResponse schema
		const validated = schemas.benchmarkResponse.parse(data);

		return validated;
	} catch (error) {
		if (error instanceof ApiError) {
			throw error;
		}

		if (error instanceof TypeError) {
			throw new ApiError(`Network error: ${error.message}`, 0);
		}

		if (error instanceof z.ZodError) {
			throw new ApiError(`Invalid response format: ${error.message}`, 422);
		}

		throw new ApiError(`Unexpected error: ${String(error)}`, 500);
	}
}

/**
 * Parse Zod validation error for user display
 */
export function formatApiError(error: unknown): string {
	if (error instanceof ApiError) {
		return error.message;
	}

	if (error instanceof Error) {
		return error.message;
	}

	return "An unknown error occurred";
}
