/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        imtiaz: {
          dark: '#0a1628',
          card: '#0d1f45',
          cardHover: '#122055',
          pink: '#E91E8C',
          pinkHover: '#ff2fa0',
          blue: '#5BC8F5',
          green: '#8DC63F',
          textMuted: '#94a8c7',
          textMutedDark: '#7a94b8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
