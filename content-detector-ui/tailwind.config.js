/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0F172A", // Dark Slate background
        card: "#1E293B",       // Slate card background
        border: "#334155",     // Border color
        success: "#22C55E",    // Green (Neutral / Verified)
        warning: "#F59E0B",    // Amber (Opinion)
        danger: "#EF4444",     // Red (Propaganda)
        primaryText: "#F8FAFC",
        secondaryText: "#94A3B8"
      }
    },
  },
  plugins: [],
}
