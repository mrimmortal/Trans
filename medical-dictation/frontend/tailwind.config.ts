import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#007AFF",
        secondary: "#5FBF6F",
        danger: "#FF3B30",
        warning: "#FF9500",
        success: "#34C759",
      },
      animation: {
        "pulse-ring": "pulse-ring 2s infinite",
        "record-pulse": "record-pulse 1s infinite",
      },
      keyframes: {
        "pulse-ring": {
          "0%": {
            "box-shadow": "0 0 0 0 rgba(0, 122, 255, 0.7)",
          },
          "70%": {
            "box-shadow": "0 0 0 10px rgba(0, 122, 255, 0)",
          },
          "100%": {
            "box-shadow": "0 0 0 0 rgba(0, 122, 255, 0)",
          },
        },
        "record-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
