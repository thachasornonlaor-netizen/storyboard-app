export default function StoryboardPanel({ storyboard, onRemove, onClear }) {
  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Storyboard{' '}
          <span className="ml-1 rounded-full bg-accent/20 px-2 py-0.5 text-xs font-bold text-accent-2">
            {storyboard.length}
          </span>
        </h2>
        {storyboard.length > 0 && (
          <button
            onClick={onClear}
            className="text-xs font-medium text-rose-400 transition hover:text-rose-300"
          >
            Clear all
          </button>
        )}
      </div>

      {storyboard.length === 0 && (
        <div className="rounded-xl border border-dashed border-white/15 p-6 text-center">
          <p className="text-xs leading-relaxed text-slate-500">
            Click "+ Add to Storyboard" on any frame to start building your shot list.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {storyboard.map((frame, i) => (
          <div
            key={i}
            className="group relative flex gap-3 rounded-xl border border-white/10 bg-panel-2 p-2.5 transition hover:border-accent/40 animate-fade-in-up"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <div className="relative shrink-0">
              <span className="absolute -left-1.5 -top-1.5 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-[10px] font-bold text-white shadow-md shadow-accent/30">
                {i + 1}
              </span>
              <img
                src={frame.image_url}
                alt={frame.description}
                className="h-14 w-20 rounded-lg object-cover"
              />
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-xs leading-snug text-slate-200">
                {frame.description}
              </p>
              <p className="mt-1 truncate text-[10px] text-slate-500">
                {frame.film} · {frame.timestamp}
              </p>
            </div>
            <button
              onClick={() => onRemove(i)}
              title="Remove from storyboard"
              className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-md bg-rose-500/20 text-rose-400 transition hover:bg-rose-500 hover:text-white"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
