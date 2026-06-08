/**
 * Standalone Vitest config — intentionally does NOT import the SvelteKit
 * vite plugin so that unit tests can run without `svelte-kit sync` or
 * the @sveltejs/vite-plugin-svelte peer dependency.
 *
 * Our unit tests only exercise pure TypeScript modules (time.ts, config.ts)
 * that have no Svelte component imports, so no Svelte transform is needed.
 */
import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  resolve: {
    alias: {
      // Replicate SvelteKit's $lib alias so imports like '$lib/utils/time' resolve
      '$lib': resolve(__dirname, './src/lib')
    }
  },
  esbuild: {
    // Use the standalone test tsconfig so vitest doesn't try to read
    // tsconfig.json which extends .svelte-kit/tsconfig.json (needs svelte-kit sync)
    tsconfigRaw: {
      compilerOptions: {
        target: 'ES2020',
        module: 'ESNext',
        moduleResolution: 'bundler',
        allowJs: true,
        esModuleInterop: true,
        resolveJsonModule: true,
        skipLibCheck: true,
        strict: true
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.ts'],
    include: ['src/tests/**/*.test.ts']
  }
});
