import { defineConfig } from 'vite'

// Pinned to 5174: 5173 and 3000 are already in use by unrelated local
// projects on this machine (finflow), so Vite's defaults collide.
export default defineConfig({
  server: {
    port: 5174,
  },
})
