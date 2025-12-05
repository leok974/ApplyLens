/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './popup.html',
    './popup.js',
    './sidepanel.html',
    './sidepanel.js',
    './contentV2.js',
  ],
  theme: {
    extend: {
      boxShadow: {
        'alp-glow': '0 0 28px rgba(56,189,248,0.55)',
      },
      borderRadius: {
        'alp-xl': '1.75rem',
        'alp-lg': '1.25rem',
      },
    },
  },
  plugins: [],
};
