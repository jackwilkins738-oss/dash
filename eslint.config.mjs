import { defineConfig, globalIgnores } from 'eslint/config'
import nextVitals from 'eslint-config-next/core-web-vitals'
import nextTypescript from 'eslint-config-next/typescript'

// Flat config, per the Next.js 16 docs. `next lint` no longer exists in this
// version, so this is run directly: `npm run lint`.
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTypescript,
  globalIgnores([
    // Default ignores of eslint-config-next:
    '.next/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    // Not source: local outreach spreadsheets and throwaway scratch files.
    'outreach/**',
    'scratch/**',
    // A separate embedded Vite project (its own package.json/node_modules/
    // eslint config) that a prior session used only as a feature-list
    // reference - not part of this app. Without this, its .cjs files (which
    // eslint-config-next's plugin registration doesn't cover - that only
    // scopes .js/.jsx/.mjs/.ts/.tsx/.mts/.cts) hit the unscoped rule below
    // and crash the whole `eslint .` run with "could not find plugin
    // react-hooks", not just warn on this directory's own files.
    'SCALAR/**',
  ]),
  {
    // Scoped to match eslint-config-next's own file set - a rule that
    // references a plugin (react-hooks) must never be reachable on a file
    // type that plugin isn't registered for, or ESLint aborts entirely
    // instead of skipping it.
    files: ['**/*.{js,jsx,mjs,ts,tsx,mts,cts}'],
    rules: {
      // A warning, not an error, and deliberately not silenced. Three
      // components set state in an effect on purpose, each to sync from
      // something that only exists in the browser after mount:
      //   google-analytics.tsx  reads the consent choice from localStorage
      //   preloader.tsx         reads the prefers-reduced-motion media query
      //   site-nav.tsx          closes the mobile menu when the route changes
      // Reading either store during render would be a hydration mismatch, so
      // the effect is the correct home for it. The rule is advisory (React's
      // "you might not need an effect") and rewriting animation-critical code
      // to satisfy it is a bigger risk than the warning is worth. New code
      // that trips it still shows up here for a second look.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
])

export default eslintConfig
