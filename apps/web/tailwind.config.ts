import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Keep your existing custom colors
        bg: 'rgb(11 13 18)',
        surface: 'rgb(16 20 27)',
        elev1: 'rgb(20 24 33)',
        elev2: 'rgb(23 28 38)',
        border: 'hsl(var(--border))',
        text: 'rgb(231 235 243)',
        subtext: 'rgb(174 184 199)',
        accent: '#2b66ff',
        // shadcn color tokens
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl2: '1rem',
      },
      boxShadow: {
        card: '0 1px 0 rgba(0,0,0,.45), 0 12px 24px rgba(0,0,0,.25)',
      },
      keyframes: {
        'accordion-down': { 
          from: { height: '0' }, 
          to: { height: 'var(--radix-accordion-content-height)' } 
        },
        'accordion-up': { 
          from: { height: 'var(--radix-accordion-content-height)' }, 
          to: { height: '0' } 
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/line-clamp'),
    require('@tailwindcss/aspect-ratio'),
    require('@tailwindcss/container-queries'),
    require('tailwindcss-animate'),
    require('tailwind-scrollbar'),
  ],
} satisfies Config
