import type { Config } from "tailwindcss";
import animatePlugin from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./styles/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Inter", "system-ui", "sans-serif"]
      },
      colors: {
        brand: "hsl(var(--brand))",
        "brand-contrast": "hsl(var(--brand-contrast))",
        ink: "hsl(var(--ink))",
        "muted-ink": "hsl(var(--muted-ink))",
        surface: "hsl(var(--surface))"
      },
      borderRadius: {
        xl: "1.5rem"
      },
      boxShadow: {
        floating: "0 20px 45px -20px rgba(15, 23, 42, 0.35)"
      }
    }
  },
  plugins: [animatePlugin]
};

export default config;
