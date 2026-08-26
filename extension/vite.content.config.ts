import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// MV3 content scripts run as plain classic scripts, so this must be one
// self-contained file with no import/export statements left in it.
export default defineConfig({
    plugins: [react()],
    build: {
        outDir: 'dist',
        emptyOutDir: false, // don't wipe the popup build from vite.config.ts
        cssCodeSplit: false,
        lib: {
            entry: new URL('src/content/content-main.tsx', import.meta.url).pathname,
            name: 'ControlPlaneContentScript',
            formats: ['iife'],
            fileName: () => 'content-main.js',
        },
    },
})