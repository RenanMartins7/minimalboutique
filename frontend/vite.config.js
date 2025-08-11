import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/products': 'http://products:5001',
            '/cart': 'http://backend:5000',
            '/checkout': 'http://backend:5000',
            '/auth': 'http://backend:5000',
            '/orders': 'http://backend:5000'
        }
    }
})