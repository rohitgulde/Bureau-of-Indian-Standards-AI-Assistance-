import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Semantic design tokens (CSS variable-driven via Shadcn)
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        // ── Government portal brand palette ──────────────────────────────
        "gov-navy": {
          DEFAULT: "#0f2d6e",   // BIS/GOI deep navy
          50:  "#eef3fb",
          100: "#d5e1f5",
          200: "#aac3eb",
          300: "#7fa5e0",
          400: "#5487d6",
          500: "#2969cb",
          600: "#1e54b0",
          700: "#173f87",
          800: "#0f2d6e", // DEFAULT
          900: "#091d49",
        },
        "gov-orange": {
          DEFAULT: "#e8521a",   // Saffron / Ashoka accent
          50:  "#fef3ed",
          100: "#fce3d3",
          200: "#f9c7a8",
          300: "#f5ab7c",
          400: "#f28f51",
          500: "#ee7325",
          600: "#e8521a", // DEFAULT
          700: "#c04014",
          800: "#97310f",
          900: "#6f230b",
        },
        "gov-slate": {
          DEFAULT: "#f1f5f9",
          50:  "#f8fafc",
          100: "#f1f5f9", // DEFAULT (page background)
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-geist-mono)", "ui-monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
        "2xl": "calc(var(--radius) + 8px)",
      },
      boxShadow: {
        "gov-sm": "0 1px 3px 0 rgb(15 45 110 / 0.10), 0 1px 2px -1px rgb(15 45 110 / 0.08)",
        "gov-md": "0 4px 12px 0 rgb(15 45 110 / 0.12), 0 2px 6px -2px rgb(15 45 110 / 0.10)",
        "gov-lg": "0 10px 30px -5px rgb(15 45 110 / 0.15)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to:   { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to:   { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition:  "200% 0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "fade-in":        "fade-in 0.3s ease-out",
        shimmer:          "shimmer 1.8s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;