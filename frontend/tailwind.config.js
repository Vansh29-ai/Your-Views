/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: 'rgb(var(--paper) / <alpha-value>)',
        'paper-deep': 'rgb(var(--paper-deep) / <alpha-value>)',
        'paper-shade': 'rgb(var(--paper-shade) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        'ink-soft': 'rgb(var(--ink-soft) / <alpha-value>)',
        rule: 'rgb(var(--rule) / <alpha-value>)',
        oxblood: 'rgb(var(--oxblood) / <alpha-value>)',
        gold: 'rgb(var(--gold) / <alpha-value>)',
      },
      fontFamily: {
        blackletter: ['"UnifrakturCook"', 'Old English Text MT', 'serif'],
        display: ['"Playfair Display"', 'Georgia', 'Times New Roman', 'serif'],
        body: ['"IM Fell English"', 'Georgia', 'serif'],
        serif: ['"Libre Baskerville"', 'Georgia', 'serif'],
        typewriter: ['"Special Elite"', 'Courier New', 'monospace'],
      },
      fontSize: {
        'masthead': ['clamp(3.4rem, 9.5vw, 8.4rem)', { lineHeight: '0.78', letterSpacing: '0.01em' }],
        'lead': ['clamp(2.3rem, 4.6vw, 4.4rem)', { lineHeight: '0.96', letterSpacing: '-0.02em' }],
        'headline': ['clamp(1.65rem, 2.5vw, 2.35rem)', { lineHeight: '1.02', letterSpacing: '-0.01em' }],
        'deck': ['clamp(1.05rem, 1.4vw, 1.3rem)', { lineHeight: '1.45' }],
      },
      maxWidth: {
        paper: '1360px',
        measure: '68ch',
      },
      borderWidth: {
        3: '3px',
      },
      transitionTimingFunction: {
        paper: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'image-in': {
          '0%': { opacity: '0', filter: 'blur(6px) sepia(.5)', transform: 'scale(1.02)' },
          '100%': { opacity: '1', filter: 'blur(0) sepia(.28)', transform: 'scale(1)' },
        },
        ticker: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'ink-in': {
          '0%': { opacity: '0', letterSpacing: '0.06em' },
          '100%': { opacity: '1', letterSpacing: 'normal' },
        },
      },
      animation: {
        'fade-up': 'fade-up .55s cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in .35s ease both',
        'image-in': 'image-in .8s cubic-bezier(0.22, 1, 0.36, 1) both',
        ticker: 'ticker 72s linear infinite',
        'ink-in': 'ink-in .6s ease both',
      },
    },
  },
  plugins: [],
}
