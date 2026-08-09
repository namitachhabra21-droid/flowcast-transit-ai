import { useCallback, useEffect, useRef, useState } from 'react'
import ApiKeyGate from './components/ApiKeyGate.jsx'
import RouteSearch from './components/RouteSearch.jsx'
import StopSchedule from './components/StopSchedule.jsx'
import { clearApiKey, fetchCrowding, fetchMe, fetchRoutes, fetchTrips, getApiKey } from './api.js'

const POLL_INTERVAL_MS = 45000

export default function App() {
  const [authed, setAuthed] = useState(() => Boolean(getApiKey()))
  const [me, setMe] = useState(null)
  const [routes, setRoutes] = useState([])
  const [routesLoading, setRoutesLoading] = useState(true)
  const [selectedRoute, setSelectedRoute] = useState(null)
  const [trips, setTrips] = useState([])
  const [tripsLoading, setTripsLoading] = useState(false)
  const [crowdingByTrip, setCrowdingByTrip] = useState({})
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    if (!authed) return undefined
    let cancelled = false
    fetchMe()
      .then((data) => !cancelled && setMe(data))
      .catch(() => !cancelled && setAuthed(false))
    return () => {
      cancelled = true
    }
  }, [authed])

  useEffect(() => {
    if (!authed) return undefined
    let cancelled = false
    fetchRoutes()
      .then((data) => {
        if (cancelled) return
        setRoutes(data)
        setError(null)
        if (data.length > 0) setSelectedRoute(data[0])
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.message)
        if (err.message.includes('401')) setAuthed(false)
      })
      .finally(() => !cancelled && setRoutesLoading(false))
    return () => {
      cancelled = true
    }
  }, [authed])

  const loadCrowding = useCallback(async (tripList) => {
    const entries = await Promise.all(
      tripList.map(async (trip) => {
        try {
          const data = await fetchCrowding(trip.id)
          return [trip.id, data]
        } catch {
          return [trip.id, null]
        }
      })
    )
    setCrowdingByTrip((prev) => {
      const next = { ...prev }
      for (const [id, data] of entries) {
        if (data) next[id] = data
      }
      return next
    })
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    if (!authed || !selectedRoute) return undefined
    let cancelled = false
    setTripsLoading(true)
    setCrowdingByTrip({})
    fetchTrips(selectedRoute.external_id)
      .then((data) => {
        if (cancelled) return
        setTrips(data)
        setError(null)
        loadCrowding(data)
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setTripsLoading(false))

    return () => {
      cancelled = true
    }
  }, [authed, selectedRoute, loadCrowding])

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (trips.length === 0) return undefined
    pollRef.current = setInterval(() => loadCrowding(trips), POLL_INTERVAL_MS)
    return () => clearInterval(pollRef.current)
  }, [trips, loadCrowding])

  function handleSignOut() {
    clearApiKey()
    setAuthed(false)
    setMe(null)
    setRoutes([])
    setSelectedRoute(null)
    setTrips([])
    setCrowdingByTrip({})
  }

  if (!authed) {
    return <ApiKeyGate onAuthenticated={() => setAuthed(true)} />
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          <span className="app__logo">&#9673;</span>
          <div>
            <h1>TransitPulse</h1>
            <p className="app__tagline">
              {me ? `${me.organization.name} · ${me.role}` : 'Predictive crowding, before you tap in.'}
            </p>
          </div>
        </div>
        <div className="app__header-right">
          {lastUpdated && (
            <div className="app__status">
              <span className="app__status-dot" />
              live &middot; updated{' '}
              {lastUpdated.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })}
            </div>
          )}
          <button type="button" className="app__signout" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      </header>

      {error && <div className="banner banner--error">{error}</div>}

      <main className="app__grid">
        <RouteSearch
          routes={routes}
          selectedRouteId={selectedRoute?.external_id}
          onSelect={setSelectedRoute}
          loading={routesLoading}
        />
        <StopSchedule route={selectedRoute} trips={trips} crowdingByTrip={crowdingByTrip} loading={tripsLoading} />
      </main>

      <footer className="app__footer">
        <div className="legend">
          <span className="legend__item">
            <i style={{ background: 'var(--level-low)' }} /> Low
          </span>
          <span className="legend__item">
            <i style={{ background: 'var(--level-medium)' }} /> Medium
          </span>
          <span className="legend__item">
            <i style={{ background: 'var(--level-high)' }} /> High
          </span>
          <span className="legend__item">
            <i style={{ background: 'var(--level-full)' }} /> Full
          </span>
        </div>
      </footer>
    </div>
  )
}
