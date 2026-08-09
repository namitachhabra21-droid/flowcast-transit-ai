import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Pinned to 5174: 5173 and 3000 are already in use by unrelated local
// projects on this machine (finflow), so Vite's defaults collide.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
  },
})
