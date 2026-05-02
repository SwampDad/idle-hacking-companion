/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      boxShadow: {
        panel: '0 8px 24px rgba(0, 0, 0, 0.42)',
      },
      borderRadius: {
        ui: '8px',
      },
    },
  },
  plugins: [],
};
