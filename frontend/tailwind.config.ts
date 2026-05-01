import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#09111f",
        paper: "#f6f2ea",
        sand: "#e4d8c6",
        ember: "#d94f2a",
        moss: "#496b54",
      },
      boxShadow: {
        panel: "0 20px 60px rgba(9, 17, 31, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
