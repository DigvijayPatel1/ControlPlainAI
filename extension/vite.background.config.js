import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

// MV3 background workers support "type": "module", so this can stay ESM.
export default defineConfig({
    build: {
        outDir: 'dist',
        emptyOutDir: false,
        lib: {
            entry: fileURLToPath(new URL('./src/background/service-worker.js', import.meta.url)),
            formats: ['es'],
            fileName: () => 'service-worker.js',
        },
    },
})
