import { useState } from 'react'

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) onSearch(query.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label className="text-sm font-semibold uppercase tracking-wider text-slate-400">
        Describe a shot
      </label>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder='e.g. "low angle close up of a car at night, tense mood, neon lighting"...'
          className="w-full rounded-xl border border-white/10 bg-panel-2 px-4 py-3 pr-28 text-base text-slate-100 placeholder-slate-500 shadow-inner transition focus:border-accent focus:ring-2 focus:ring-accent/30 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="absolute inset-y-1.5 right-1.5 rounded-lg bg-gradient-to-r from-accent to-accent-2 px-5 text-base font-semibold text-white shadow-lg shadow-accent/25 transition hover:brightness-110 disabled:cursor-not-allowed disabled:from-slate-600 disabled:to-slate-600 disabled:shadow-none"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </form>
  )
}
