import FrameCard from './FrameCard'

export default function ResultsGrid({ results, onAdd }) {
  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-panel-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-8 w-8 text-slate-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
        </div>
        <p className="mt-4 text-sm text-slate-400">
          No frames found. Try a different search or adjust your filters.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {results.map((frame, i) => (
        <FrameCard key={frame.filename || i} frame={frame} onAdd={onAdd} index={i} />
      ))}
    </div>
  )
}
