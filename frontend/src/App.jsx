import { useState, useEffect, useRef } from 'react'
import SearchBar from './components/SearchBar'
import FilterPanel from './components/FilterPanel'
import ResultsGrid from './components/ResultsGrid'
import StoryboardPanel from './components/StoryboardPanel'
import LandingPage from './components/LandingPage'
import { apiUrl } from './config'

function App() {
  const [started, setStarted] = useState(false)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [storyboard, setStoryboard] = useState([])
  const [cachedMovies, setCachedMovies] = useState([])
  const [metadataFilters, setMetadataFilters] = useState({})
  const [selectedFilters, setSelectedFilters] = useState({
    camera_angle: [], shot_size: [],
    mood: [], tone: [], lighting: []
  })
  const [lastQuery, setLastQuery] = useState('')
  const [error, setError] = useState('')
  const [appliedFilters, setAppliedFilters] = useState({})
  const lastQueryRef = useRef('')
  const searchReqRef = useRef(0)

  useEffect(() => {
    fetchFilters()
  }, [])

  const fetchFilters = () => {
    fetch(apiUrl('/api/filters')).then(r => r.json())
      .then(data => {
        setCachedMovies(data.movies || [])
        const meta = {}
        const cats = ['camera_angle', 'shot_size', 'mood', 'tone', 'lighting']
        cats.forEach(c => { meta[c] = data[c] || [] })
        setMetadataFilters(meta)
      })
      .catch(() => {})
  }

  const buildFilterParams = (query, filters) => {
    const params = new URLSearchParams()
    if (query.trim()) params.set('q', query.trim())
    for (const [cat, values] of Object.entries(filters)) {
      if (values.length > 0) {
        params.set(cat, values.join(','))
      }
    }
    return params.toString()
  }

  const pollSearch = async (qs) => {
    const myReq = ++searchReqRef.current
    let res = await fetch(apiUrl(`/api/search?${qs}`), { method: 'POST' })
    if (!res.ok) throw new Error('Search failed')
    const { job_id } = await res.json()
    if (!job_id) throw new Error('Search failed')

    let failures = 0
    while (searchReqRef.current === myReq) {
      await new Promise(r => setTimeout(r, 4000))
      try {
        res = await fetch(apiUrl(`/api/search/status?job_id=${encodeURIComponent(job_id)}`))
        const data = await res.json()
        if (data.status === 'done') {
          setResults(data.frames || [])
          setAppliedFilters(data.applied_filters || {})
          if (!data.frames || data.frames.length === 0) {
            setError(data.error || 'No matching frames found.')
          }
          fetchFilters()
          return
        }
        if (data.status === 'error' || data.status === 'not_found') {
          throw new Error(data.error || 'Search failed.')
        }
        failures = 0
      } catch (err) {
        failures += 1
        if (failures >= 3) throw err
      }
    }
  }

  const searchFrames = async (query, filters) => {
    const effectiveQuery = query || ''
    const effectiveFilters = filters || selectedFilters
    const qs = buildFilterParams(effectiveQuery, effectiveFilters)
    if (!qs) return

    setLoading(true)
    setError('')
    setLastQuery(effectiveQuery)
    lastQueryRef.current = effectiveQuery
    try {
      await pollSearch(qs)
    } catch (err) {
      setError('Search failed.')
    }
    setLoading(false)
  }

  const browseMovie = async (movieSlug) => {
    setLoading(true)
    setError('')
    try {
      await pollSearch(`film=${encodeURIComponent(movieSlug)}`)
    } catch (err) {
      setError('Search failed.')
    }
    setLoading(false)
  }

  const handleFilterChange = (newFilters) => {
    setSelectedFilters(newFilters)
    searchFrames(lastQueryRef.current, newFilters)
  }

  const addToStoryboard = (frame) => {
    setStoryboard(prev => [...prev, frame])
  }

  const removeFromStoryboard = (idx) => {
    setStoryboard(prev => prev.filter((_, i) => i !== idx))
  }

  const clearStoryboard = () => {
    setStoryboard([])
  }

  const hasResults = results.length > 0

  const appliedFilterEntries = Object.entries(appliedFilters)
    .filter(([, vals]) => vals && vals.length > 0)

  const formatFilterLabel = (val) =>
    val.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  if (!started) {
    return <LandingPage onEnter={() => setStarted(true)} />
  }

  return (
    <div className="flex h-screen flex-col bg-surface text-slate-200 animate-fade-in-up">
      <header className="flex items-center justify-between border-b border-white/10 bg-panel/70 px-6 py-4 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <img
            src="/frame-finder-logo.png"
            alt="FrameFinder AI logo"
            className="h-11 w-auto animate-float drop-shadow-[0_0_12px_rgba(129,140,248,0.35)]"
          />
          <div>
            <h1 className="bg-gradient-to-r from-accent-2 to-glow bg-clip-text text-2xl font-bold tracking-tight text-transparent">
              FrameFinder AI
            </h1>
            <p className="text-sm text-slate-400">
              Describe the shot you want — AI finds matching frames from movie trailers
            </p>
          </div>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-400 sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-glow" />
          Semantic frame search
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 shrink-0 space-y-6 overflow-y-auto border-r border-white/10 bg-panel/40 p-5">
          <SearchBar onSearch={(q) => searchFrames(q, selectedFilters)} loading={loading} />
          <FilterPanel
            movies={cachedMovies}
            onBrowse={browseMovie}
            metadataFilters={metadataFilters}
            selected={selectedFilters}
            onFilterChange={handleFilterChange}
          />
        </aside>

        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-6xl">
            <div className="mb-5 flex items-center justify-between">
              {hasResults ? (
                <h2 className="text-base font-semibold uppercase tracking-wider text-slate-400">
                  {results.length} frames found
                </h2>
              ) : (
                !loading && (
                  <h2 className="text-base font-semibold uppercase tracking-wider text-slate-400">
                    Search results
                  </h2>
                )
              )}
              {appliedFilterEntries.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-slate-500">Detected:</span>
                  {appliedFilterEntries.map(([cat, vals]) =>
                    vals.map(v => (
                      <span
                        key={`${cat}-${v}`}
                        className="rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-sm font-medium text-glow"
                      >
                        {formatFilterLabel(v)}
                      </span>
                    ))
                  )}
                </div>
              )}
            </div>

            {loading && (
              <div className="flex flex-col items-center justify-center py-32 text-center">
                <div className="h-12 w-12 animate-spin rounded-full border-4 border-accent/20 border-t-accent-2" />
                <p className="mt-4 text-base text-slate-400 animate-pulse-glow">
                  Searching frames...
                </p>
              </div>
            )}

            {error && !loading && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-5 py-4 text-base text-rose-300">
                {error}
              </div>
            )}

            {!loading && <ResultsGrid results={results} onAdd={addToStoryboard} />}
          </div>
        </main>

        <aside className="w-80 shrink-0 overflow-y-auto border-l border-white/10 bg-panel/40">
          <StoryboardPanel
            storyboard={storyboard}
            onRemove={removeFromStoryboard}
            onClear={clearStoryboard}
          />
        </aside>
      </div>
    </div>
  )
}

export default App
