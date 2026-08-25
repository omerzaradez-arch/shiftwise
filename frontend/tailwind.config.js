/** @type {import('tailwindcss').Config} */

// The palette is remapped at the scale level on purpose. Colour is hardcoded in
// ~960 places across the pages (text-slate-400, bg-indigo-600 …), so redefining
// `slate` and `indigo` themselves repaints the whole app coherently instead of
// leaving half of it on Tailwind's stock blues.

// Warm paper → ink. Deliberately yellow-biased so it never reads as the
// blue-grey every generated dashboard ships with.
const sand = {
  50:  '#FAF8F4',
  100: '#F2EFE8',
  200: '#E4DFD5',
  300: '#CFC8BA',
  400: '#A69C8C',
  500: '#7D7365',
  600: '#5E5648',
  700: '#453F35',
  800: '#2E2A24',
  900: '#1E1B17',
  950: '#141210',
}

// Vermilion — a marker stroke, a stamp. Carries every primary action.
const vermilion = {
  50:  '#FDF2EE',
  100: '#FBE0D7',
  200: '#F5BFAE',
  300: '#EE9A80',
  400: '#E2725B',
  500: '#D45A40',
  600: '#B8452C',
  700: '#95371F',
  800: '#742C1A',
  900: '#552217',
  950: '#331209',
}

// Quiet counterweight: used for information and secondary state, never for
// primary actions, so the vermilion keeps all of its force.
const verdigris = {
  50:  '#EFF5F3',
  100: '#DAE7E3',
  200: '#B6CFC8',
  300: '#8CB2A8',
  400: '#5F9184',
  500: '#437366',
  600: '#345C52',
  700: '#2A4941',
  800: '#213833',
  900: '#1A2C28',
  950: '#101C19',
}

module.exports = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },

        // Scale remaps — these are what the existing markup actually reaches for.
        slate: sand,
        gray: sand,
        zinc: sand,
        neutral: sand,
        stone: sand,
        indigo: vermilion,
        blue: vermilion,
        violet: verdigris,
        purple: verdigris,
        teal: verdigris,
        emerald: verdigris,

        sand,
        vermilion,
        verdigris,

        // Shift tags, as tinted paper stock rather than pastel chips.
        shift: {
          morning:   '#FBE9CB',
          afternoon: '#DAE7E3',
          evening:   '#E8DCE6',
          night:     '#2E2A24',
        },
      },

      // Tight geometry. The stock 0.75rem pill is the single loudest tell of a
      // generated interface; this reads as an instrument instead.
      borderRadius: {
        none: '0',
        sm: '2px',
        DEFAULT: '3px',
        md: '4px',
        lg: '5px',
        xl: '6px',
        '2xl': '8px',
        '3xl': '10px',
        full: '9999px',
      },

      fontFamily: {
        sans: ['var(--font-assistant)', 'system-ui', 'sans-serif'],
        display: ['var(--font-frank)', 'Georgia', 'serif'],
        mono: ['var(--font-plex-mono)', 'ui-monospace', 'monospace'],
      },

      letterSpacing: {
        tightest: '-0.04em',
        label: '0.08em',
      },

      boxShadow: {
        card: '0 1px 2px rgba(30,27,23,.05), 0 8px 24px -18px rgba(30,27,23,.35)',
        lift: '0 2px 4px rgba(30,27,23,.06), 0 16px 40px -24px rgba(30,27,23,.45)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
