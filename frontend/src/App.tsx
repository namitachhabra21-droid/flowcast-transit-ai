import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { NetworkClock, PassengerCount } from './LiveMetrics'

type PortalTargetId =
  | 'reactPassengerCount'
  | 'reactMapClock'

function getPortalTarget(id: PortalTargetId): HTMLElement {
  const target = document.getElementById(id)
  if (!target) throw new Error(`Missing React portal target: ${id}`)
  return target
}

export function App() {
  useEffect(() => {
    // Preserve the existing feature set while individual dashboard areas are
    // progressively converted into fully declarative React components.
    void import('./legacyInteractions')
  }, [])

  return (
    <>
      {createPortal(<PassengerCount />, getPortalTarget('reactPassengerCount'))}
      {createPortal(<NetworkClock />, getPortalTarget('reactMapClock'))}
    </>
  )
}
