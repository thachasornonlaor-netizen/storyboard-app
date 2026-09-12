import { useState } from 'react'

export default function FilterPanel({ movies, onBrowse, metadataFilters, selected, onFilterChange }) {
  const categories = [
    { key: 'camera_angle', label: 'Camera Angle' },
    { key: 'shot_size', label: 'Shot Size' },
    { key: 'mood', label: 'Mood' },
    { key: 'tone', label: 'Tone' },
    { key: 'lighting', label: 'Lighting' }
  ]

  const [openCats, setOpenCats] = useState(() =>
    new Set(categories.map(c => c.key))
  )

  const toggleCategory = (key) => {
    setOpenCats(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  const toggle = (category, value) => {
    const current = selected[category] || []
    const next = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]
    onFilterChange({ ...selected, [category]: next })
  }

  const hasSelections = Object.values(selected).some(arr => arr.length > 0)

  function formatLabel(str) {
    return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Recent Movies
        </h3>
        {!movies || movies.length === 0 ? (
          <p className="text-sm text-slate-500">Search for a movie to see its frames here.</p>
        ) : (
          <div className="space-y-2">
            {movies.map(m => (
              <button
                key={m.slug}
                onClick={() => onBrowse(m.slug)}
                className="group flex w-full items-center justify-between rounded-xl border border-white/10 bg-panel-2 px-3.5 py-3 text-left transition hover:border-accent/50 hover:bg-accent/10"
              >
                <span className="truncate text-base font-medium text-slate-200 group-hover:text-white">
                  {m.title}
                </span>
                <span className="ml-3 shrink-0 rounded-full bg-white/5 px-2.5 py-1 text-xs text-slate-400">
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
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Metadata Filters
          </h3>
          {hasSelections && (
            <button
              className="text-sm font-medium text-accent-2 transition hover:text-glow"
              onClick={() => onFilterChange({
                camera_angle: [], shot_size: [],
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
          const selectedCount = (selected[cat.key] || []).length
          const isOpen = openCats.has(cat.key)
          return (
            <div
              key={cat.key}
              className="mb-2 overflow-hidden rounded-xl border border-white/10 bg-panel-2 transition hover:border-accent/30"
            >
              <button
                type="button"
                onClick={() => toggleCategory(cat.key)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-white/5"
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                  {cat.label}
                  {selectedCount > 0 && (
                    <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-bold text-white shadow-sm shadow-accent/30">
                      {selectedCount}
                    </span>
                  )}
                </span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </button>
              <div className={`grid transition-all duration-300 ${isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
                <div className="min-h-0 overflow-hidden">
                  <div className="flex flex-wrap gap-1.5 border-t border-white/10 px-4 py-3">
                    {options.map(value => {
                      const checked = (selected[cat.key] || []).includes(value)
                      return (
                        <button
                          key={value}
                          type="button"
                          onClick={() => toggle(cat.key, value)}
                          className={`rounded-full border px-3 py-1.5 text-sm font-medium transition active:scale-95 ${
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
              </div>
            </div>
          )
        })}

        {categories.every(cat => !metadataFilters[cat.key] || metadataFilters[cat.key].length === 0) && (
          <p className="text-sm text-slate-500">
            No metadata filters available yet. Add tags to frames to enable filtering.
          </p>
        )}
      </section>
    </div>
  )
}
