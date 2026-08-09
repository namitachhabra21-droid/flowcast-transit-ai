import React from 'react'
import { createRoot } from 'react-dom/client'
import { LiveStatus, NetworkClock, PassengerCount } from './LiveMetrics.jsx'

createRoot(document.getElementById('reactLiveStatus')).render(<LiveStatus />)
createRoot(document.getElementById('reactPassengerCount')).render(<PassengerCount />)
createRoot(document.getElementById('reactMapClock')).render(<NetworkClock />)

// The existing dashboard is progressively migrating to React. Load the
// interaction layer after the first React render so both systems stay stable.
window.requestAnimationFrame(() => import('../app.js'))
