/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Core standard colors mapped to variables for flexibility
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        
        // DataLab Specific Colors
        primary: {
          DEFAULT: "#81d8cf", // Tiffany Blue
          foreground: '#0F172A',
          50: '#f2fcfb',
          100: '#e6f9f7',
          200: '#cbf2ee',
          300: '#a0e6df',
          400: '#81d8cf', // Base
          500: '#4cc0b5',
          600: '#3aa299',
          700: '#32827c',
          800: '#2d6864',
          900: '#275653',
          950: '#153332',
        },
        // Tiffany Blue - 独立颜色键用于渐变
        tiffany: {
          50: '#f2fcfb',
          100: '#e6f9f7',
          200: '#cbf2ee',
          300: '#a0e6df',
          400: '#4cc0b5',
          500: '#3aa299',
          600: '#32827c',
          700: '#2d6864',
          800: '#275653',
          900: '#153332',
          950: '#0d2928',
        },
        // 新增：文档页面专用Tiffany Blue (#00BFB3)
        'doc-tiffany': {
          DEFAULT: '#00BFB3',
          50: '#E6F9F8',
          100: '#B3F0ED',
          200: '#80E8E2',
          300: '#4DE0D7',
          400: '#1AD8CC',
          500: '#00BFB3',
          600: '#00A89D',
          700: '#009187',
          800: '#007A71',
          900: '#00635B',
        },
        secondary: {
          DEFAULT: "#b9ede8", // Clean Cyan
          foreground: '#0F172A',
        },
        "background-light": "#f0fafa", // Very subtle cyan tint
        "background-dark": "#0f172a", // Slate 900
        "surface-light": "#ffffff",
        "surface-dark": "#1e293b", // Slate 800
        "accent-light": "#e0f7f5",
        "accent-dark": "#164e63",

        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
      },
      fontFamily: {
        sans: ['Inter', 'var(--font-fira-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-fira-code)', 'monospace'],
        display: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        DEFAULT: "0.5rem",
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(129, 216, 207, 0.1)',
        'glow': '0 0 15px rgba(129, 216, 207, 0.3)',
      },
      animation: {
        'subtle-pulse': 'subtle-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
      },
      keyframes: {
        'subtle-pulse': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [require('@tailwindcss/forms'), require('@tailwindcss/typography')],
}