import { createRoot } from 'react-dom/client'
import { App } from './App'

const rootElement = document.getElementById('reactRuntimeRoot')

if (!rootElement) {
  throw new Error('React runtime root was not found')
}

createRoot(rootElement).render(<App />)
