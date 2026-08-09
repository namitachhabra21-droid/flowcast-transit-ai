import { useState } from 'react'
import { setApiKey } from '../api.js'

export default function ApiKeyGate({ onAuthenticated }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!value.trim()) return
    setApiKey(value)
    onAuthenticated()
  }

  return (
    <div className="gate">
      <div className="gate__card">
        <div className="gate__logo">&#9673;</div>
        <h1>TransitPulse</h1>
        <p className="muted">
          No Clerk sign-in configured yet for this local build. Paste an org API key to continue — generate one from
          the backend with:
        </p>
        <pre className="gate__code">python -m app.scripts.seed_dev_org</pre>
        <form onSubmit={handleSubmit} className="gate__form">
          <input
            type="text"
            placeholder="tc_..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
          />
          <button type="submit">Continue</button>
        </form>
      </div>
    </div>
  )
}
