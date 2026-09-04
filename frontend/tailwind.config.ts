import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07090c",
          900: "#0c1116",
          800: "#121820",
          700: "#182028",
          600: "#243040",
        },
        mist: {
          100: "#e8eef4",
          300: "#b7c3cf",
          500: "#7d8b99",
        },
        teal: {
          DEFAULT: "#5eead4",
          dim: "#2dd4bf",
        },
      },
      fontFamily: {
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(94, 234, 212, 0.08), 0 24px 60px rgba(0,0,0,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
