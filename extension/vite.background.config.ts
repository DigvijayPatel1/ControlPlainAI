import { defineConfig } from 'vite'

// MV3 background workers support "type": "module", so this can stay ESM.
export default defineConfig({
    build: {
        outDir: 'dist',
        emptyOutDir: false,
        lib: {
            entry: new URL('src/background/service-worker.ts', import.meta.url).pathname,
            formats: ['es'],
            fileName: () => 'service-worker.js',
        },
    },
})