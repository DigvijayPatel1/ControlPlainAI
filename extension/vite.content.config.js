import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'


export default defineConfig({
    plugins: [react(), tailwindcss()],
    define: {
        'process.env.NODE_ENV': JSON.stringify('production'),
    },
    build: {
        outDir: 'dist',
        emptyOutDir: false,
        cssCodeSplit: false,
        lib: {
            entry: fileURLToPath(new URL('./src/content/Content-main.jsx', import.meta.url)),
            name: 'ControlPlaneContentScript',
            formats: ['iife'],
            fileName: () => 'content-main.js',
        },
    },
})
