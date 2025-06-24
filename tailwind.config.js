/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./docs/**/*.{html,js,md}",
    "./overrides/**/*.{html,js}"
  ],
  theme: {
    extend: {
      colors: {
        // Light mode colors
        primary: {
          DEFAULT: '#000000', // Black for primary text
          light: '#333333',   // Light black for secondary text
          dark: '#000000',    // Black for emphasis
        },
        accent: {
          DEFAULT: '#000000',
          transparent: 'rgba(0, 0, 0, 0.05)',
        },
        // Category colors - more muted and monochromatic
        category: {
          documentation: '#3B82F6', // Blue
          'infrastructure-deployment': '#6B7280', // Gray
          'ai-ml': '#8B5CF6', // Purple
          'data-analytics': '#10B981', // Green
          'developer-tools': '#6B7280', // Gray
          'integration-messaging': '#6B7280', // Gray
          'cost-operations': '#6B7280', // Gray
          core: '#000000', // Black
        },
        // Status colors
        status: {
          success: '#10B981', // Green
          warning: '#F59E0B', // Amber
          error: '#EF4444',   // Red
          info: '#3B82F6',    // Blue
        },
        // AWS specific colors
        aws: {
          'dark-blue': '#232f3e',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Inter"', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        mono: ['"SF Mono"', 'Menlo', 'Monaco', '"Cascadia Code"', '"Roboto Mono"', 'Consolas', '"Courier New"', 'monospace'],
      },
      boxShadow: {
        'z1': '0 1px 2px rgba(0, 0, 0, 0.03)',
        'z2': '0 1px 3px rgba(0, 0, 0, 0.05)',
        'z3': '0 2px 4px rgba(0, 0, 0, 0.05)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        'DEFAULT': '0.375rem',
        'card': '0.5rem',
      },
    },
  },
  plugins: [],
  // Enable dark mode based on data-md-color-scheme="slate"
  darkMode: ['class', '[data-md-color-scheme="slate"]'],
}
