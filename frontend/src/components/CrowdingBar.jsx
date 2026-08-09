const LEVEL_META = {
  low: { color: 'var(--level-low)', label: 'Low' },
  medium: { color: 'var(--level-medium)', label: 'Medium' },
  high: { color: 'var(--level-high)', label: 'High' },
  full: { color: 'var(--level-full)', label: 'Full' },
}

/**
 * A miniature transit-line diagram for one trip: the track is the route's
 * line color, each station is a dot colored by its predicted crowding
 * level. Terminus stops are labeled; every dot carries the full detail as
 * a tooltip.
 */
export default function CrowdingBar({ stops, crowding, lineColor }) {
  const crowdingByStopId = new Map((crowding?.stops ?? []).map((s) => [s.stop_id, s]))

  return (
    <div className="line">
      <div className="line__track-wrap">
        <span className="line__track" style={{ background: lineColor }} />
        <div className="line__dots" role="img" aria-label="Route with predicted crowding per stop">
          {stops.map((stop) => {
            const c = crowdingByStopId.get(stop.id)
            const meta = c ? LEVEL_META[c.level] : null
            return (
              <span
                key={stop.id}
                className={`line__dot${meta ? '' : ' line__dot--pending'}`}
                style={meta ? { background: meta.color, boxShadow: `0 0 7px ${meta.color}` } : undefined}
                title={c ? `${stop.name} — ${meta.label} crowding (${Math.round(c.score * 100)}%)` : stop.name}
              />
            )
          })}
        </div>
      </div>
      <div className="line__endpoints">
        <span>{stops[0]?.name}</span>
        <span>{stops[stops.length - 1]?.name}</span>
      </div>
    </div>
  )
}
