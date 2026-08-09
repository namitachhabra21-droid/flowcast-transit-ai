import CrowdingBar from './CrowdingBar.jsx'
import { LINE_COLORS } from './RouteSearch.jsx'

function formatTime(isoString) {
  const d = new Date(isoString)
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function minutesUntil(isoString) {
  const diffMs = new Date(isoString).getTime() - Date.now()
  const mins = Math.round(diffMs / 60000)
  if (mins <= 0) return 'Due'
  if (mins === 1) return '1 min'
  return `${mins} min`
}

export default function StopSchedule({ route, trips, crowdingByTrip, loading }) {
  if (!route) {
    return (
      <section className="panel schedule">
        <p className="muted">Select a line to see upcoming departures.</p>
      </section>
    )
  }

  const lineColor = LINE_COLORS[route.external_id] ?? '#8b93a7'

  return (
    <section className="panel schedule">
      <div className="schedule__header">
        <span className="schedule__badge" style={{ background: lineColor }}>
          {route.external_id}
        </span>
        <h2 className="panel__title">
          {route.name} <span className="panel__subtitle">upcoming departures</span>
        </h2>
      </div>
      {loading && <p className="muted">Loading schedule&hellip;</p>}
      {!loading && trips.length === 0 && <p className="muted">No upcoming trips found.</p>}
      <ul className="trip-list">
        {trips.map((trip, idx) => {
          const crowding = crowdingByTrip[trip.id]
          return (
            <li key={trip.id} className="trip-row">
              <div className="trip-row__time">
                <span className="trip-row__clock">{formatTime(trip.departure_time)}</span>
                <span className={`trip-row__countdown${idx === 0 ? ' trip-row__countdown--next' : ''}`}>
                  {minutesUntil(trip.departure_time)}
                </span>
              </div>
              <div className="trip-row__body">
                <CrowdingBar stops={trip.stops} crowding={crowding} lineColor={lineColor} />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
