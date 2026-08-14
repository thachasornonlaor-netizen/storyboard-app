export default function FilterPanel({ movies, onBrowse, metadataFilters, selected, onFilterChange }) {
  const toggle = (category, value) => {
    const current = selected[category] || []
    const next = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]
    onFilterChange({ ...selected, [category]: next })
  }

  const categories = [
    { key: 'camera_angle', label: 'Camera Angle' },
    { key: 'shot_size', label: 'Shot Size' },
    { key: 'camera_movement', label: 'Camera Movement' },
    { key: 'mood', label: 'Mood' },
    { key: 'tone', label: 'Tone' },
    { key: 'lighting', label: 'Lighting' }
  ]

  const hasSelections = Object.values(selected).some(arr => arr.length > 0)

  function formatLabel(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Recent Movies
        </h3>
        {!movies || movies.length === 0 ? (
          <p className="text-xs text-slate-500">Search for a movie to see its frames here.</p>
        ) : (
          <div className="space-y-2">
            {movies.map(m => (
              <button
                key={m.slug}
                onClick={() => onBrowse(m.slug)}
                className="group flex w-full items-center justify-between rounded-xl border border-white/10 bg-panel-2 px-3.5 py-2.5 text-left transition hover:border-accent/50 hover:bg-accent/10"
              >
                <span className="truncate text-sm font-medium text-slate-200 group-hover:text-white">
                  {m.title}
                </span>
                <span className="ml-3 shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-slate-400">
                  {m.frame_count} frames
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      <div className="h-px bg-white/10" />

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Metadata Filters
          </h3>
          {hasSelections && (
            <button
              className="text-xs font-medium text-accent-2 transition hover:text-glow"
              onClick={() => onFilterChange({
                camera_angle: [], shot_size: [], camera_movement: [],
                mood: [], tone: [], lighting: []
              })}
            >
              Clear all
            </button>
          )}
        </div>

        {categories.map(cat => {
          const options = metadataFilters[cat.key]
          if (!options || options.length === 0) return null
          return (
            <div key={cat.key} className="mb-4">
              <h4 className="mb-2 text-[11px] font-medium text-slate-500">{cat.label}</h4>
              <div className="flex flex-wrap gap-1.5">
                {options.map(value => {
                  const checked = (selected[cat.key] || []).includes(value)
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => toggle(cat.key, value)}
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
                        checked
                          ? 'border-accent bg-accent text-white shadow-md shadow-accent/25'
                          : 'border-white/10 bg-white/5 text-slate-300 hover:border-accent/40 hover:bg-accent/10'
                      }`}
                    >
                      {formatLabel(value)}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}

        {categories.every(cat => !metadataFilters[cat.key] || metadataFilters[cat.key].length === 0) && (
          <p className="text-xs text-slate-500">
            No metadata filters available yet. Add tags to frames to enable filtering.
          </p>
        )}
      </section>
    </div>
  )
}
