import type { Config } from "tailwindcss";

/**
 * Tailwind v4 configuration.
 *
 * Theme tokens (color, typography, elevation, motion, spacing) are defined
 * as CSS custom properties in `src/app/globals.css` via `@theme` and `:root`,
 * which is the Tailwind v4 CSS-first approach.
 *
 * Semantic design tokens (--ds-*) live in `:root`.
 * Tailwind utility wiring (--color-ds-*: var(--ds-*)) lives in `@theme`.
 *
 * No raw hex values should be added to this file for design-token colors.
 * Reference CSS variables instead.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx,js,jsx}"],
};

export default config;
