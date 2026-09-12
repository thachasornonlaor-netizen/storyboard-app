import { frameUrl } from '../config'

const TAG_COLORS = {
  camera_angle: 'bg-indigo-500/15 text-indigo-300 border-indigo-400/30',
  shot_size: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
  mood: 'bg-rose-500/15 text-rose-300 border-rose-400/30',
  tone: 'bg-yellow-500/15 text-yellow-300 border-yellow-400/30',
  lighting: 'bg-sky-500/15 text-sky-300 border-sky-400/30'
}

export default function FrameCard({ frame, onAdd, index }) {
  return (
    <div
      className="group flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-panel-2 shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-accent/10 animate-fade-in-up"
      style={{ animationDelay: `${Math.min(index, 9) * 40}ms` }}
    >
      <div className="relative overflow-hidden">
        <img
          src={frameUrl(frame.image_url)}
          alt={frame.description}
          loading="lazy"
          className="h-48 w-full object-cover transition duration-300 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 transition group-hover:opacity-100" />
        {frame.timestamp && (
          <span className="absolute bottom-2 left-2 rounded-md bg-black/70 px-2.5 py-1 font-mono text-xs text-accent-2 backdrop-blur-sm">
            @{frame.timestamp}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="mb-1 text-sm font-medium uppercase tracking-wide text-slate-500">
          {frame.film}
        </p>

        {frame.description && (
          <p className="mb-3 line-clamp-3 text-base leading-snug text-slate-200">
            {frame.description}
          </p>
        )}

        {(frame.camera_angle || frame.shot_size || frame.mood || frame.tone || frame.lighting) && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {frame.camera_angle && <Tag label={frame.camera_angle} cls={TAG_COLORS.camera_angle} />}
            {frame.shot_size && <Tag label={frame.shot_size} cls={TAG_COLORS.shot_size} />}
            {frame.mood && <Tag label={frame.mood} cls={TAG_COLORS.mood} />}
            {frame.tone && <Tag label={frame.tone} cls={TAG_COLORS.tone} />}
            {frame.lighting && <Tag label={frame.lighting} cls={TAG_COLORS.lighting} />}
          </div>
        )}

        {frame.score !== undefined && (
          <div className="mb-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Match</span>
              <span className="font-semibold text-accent-2">
                {Math.round(frame.score * 100)}%
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
                style={{ width: `${Math.round(frame.score * 100)}%` }}
              />
            </div>
          </div>
        )}

        {frame.vlm && (
          <p className="mb-2 border-l-2 border-accent/40 pl-2 text-xs italic leading-snug text-glow/80">
            {frame.vlm.reason}
          </p>
        )}
      </div>

      <button
        onClick={() => onAdd(frame)}
        className="flex items-center justify-center gap-1.5 border-t border-white/10 bg-white/5 py-3 text-base font-semibold text-accent-2 transition hover:bg-accent hover:text-white active:scale-[0.99]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add to Storyboard
      </button>
    </div>
  )
}

function Tag({ label, cls }) {
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {formatLabel(label)}
    </span>
  )
}

function formatLabel(str) {
  return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
