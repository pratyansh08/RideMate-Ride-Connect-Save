/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0b0b",
        coal: "#151515",
        slate: "#222222",
        mist: "#e5e7eb",
        fog: "#f5f5f5",
        lime: "#1dbf73",
      },
      fontFamily: {
        display: ["\"Space Grotesk\"", "system-ui", "sans-serif"],
        body: ["\"Inter\"", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 20px 50px rgba(0, 0, 0, 0.08)",
      },
    },
  },
  plugins: [],
};
