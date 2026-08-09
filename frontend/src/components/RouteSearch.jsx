const LINE_COLORS = {
  R1: '#ff4d5e',
  B2: '#3fa7ff',
  G3: '#33d17a',
  Y4: '#f7c948',
}

export default function RouteSearch({ routes, selectedRouteId, onSelect, loading }) {
  return (
    <section className="panel route-search">
      <h2 className="panel__title">
        <span className="panel__title-glyph">&#8942;</span> Choose a line
      </h2>
      {loading && <p className="muted">Loading routes&hellip;</p>}
      <ul className="route-list">
        {routes.map((route) => {
          const isActive = route.external_id === selectedRouteId
          const color = LINE_COLORS[route.external_id] ?? '#9aa5b1'
          return (
            <li key={route.id}>
              <button
                type="button"
                className={`route-chip${isActive ? ' route-chip--active' : ''}`}
                style={{ '--line-color': color }}
                onClick={() => onSelect(route)}
              >
                <span className="route-chip__badge">{route.external_id}</span>
                <span className="route-chip__name">{route.name}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export { LINE_COLORS }
