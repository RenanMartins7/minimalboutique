import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/products': 'http://backend:5000',
            '/cart': 'http://backend:5000',
            '/checkout': 'http://backend:5000'
        }
    }
})