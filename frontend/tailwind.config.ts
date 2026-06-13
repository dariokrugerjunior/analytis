import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "768px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          base: "#0f172a",
          elevated: "#1e1b4b",
          overlay: "rgba(255,255,255,0.05)",
        },
        fg: {
          primary: "#f1f5f9",
          muted: "#94a3b8",
          subtle: "#475569",
        },
        brand: {
          primary: "#10b981",
          accent: "#fbbf24",
          danger: "#ef4444",
        },
        outcome: {
          home: "#10b981",
          draw: "#9ca3af",
          away: "#ef4444",
        },
        edge: {
          high: "#10b981",
          medium: "#fbbf24",
          low: "#94a3b8",
        },
        border: "rgba(255,255,255,0.08)",
        input: "rgba(255,255,255,0.06)",
        ring: "#fbbf24",
        background: "#0f172a",
        foreground: "#f1f5f9",
        primary: {
          DEFAULT: "#10b981",
          foreground: "#0f172a",
        },
        secondary: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
        muted: {
          DEFAULT: "#1e293b",
          foreground: "#94a3b8",
        },
        accent: {
          DEFAULT: "#fbbf24",
          foreground: "#451a03",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#f1f5f9",
        },
        card: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
        popover: {
          DEFAULT: "#1e1b4b",
          foreground: "#f1f5f9",
        },
      },
      borderRadius: {
        lg: "0.625rem",
        md: "calc(0.625rem - 2px)",
        sm: "calc(0.625rem - 4px)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
