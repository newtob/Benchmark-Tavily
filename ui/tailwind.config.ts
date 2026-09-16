import type { Config } from "tailwindcss";

const config = {
	content: ["./src/**/*.{html,js,svelte,ts}"],
	theme: {
		extend: {
			colors: {
				background: "var(--bg)",
				surface: "var(--surface)",
				"surface-2": "var(--surface-2)",
				fg1: "var(--fg1)",
				fg2: "var(--fg2)",
				fg3: "var(--fg3)",
				border: "var(--border)",
				"syn-yellow": "var(--syn-yellow)",
				"syn-blue": "var(--syn-blue)",
				"syn-blue-light": "var(--syn-blue-light)",
				success: "var(--color-success)",
				warning: "var(--color-warning)",
				error: "var(--color-error)",
				info: "var(--color-info)",
			},
		},
	},
	plugins: [],
} satisfies Config;

export default config;
