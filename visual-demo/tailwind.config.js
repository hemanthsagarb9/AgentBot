/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'state-not-started': '#9ca3af',
        'state-forms-raised': '#f59e0b',
        'state-creds-issued': '#3b82f6',
        'state-access-provisioned': '#10b981',
        'state-validated': '#6366f1',
        'state-signoff-sent': '#ec4899',
        'state-approved': '#22c55e',
        'state-complete': '#16a34a',
        'state-blocked': '#ef4444',
        'state-changes-requested': '#f87171',
      }
    },
  },
  plugins: [],
}

