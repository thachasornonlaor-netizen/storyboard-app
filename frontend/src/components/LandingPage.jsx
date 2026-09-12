export default function LandingPage({ onEnter }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-surface px-6 text-center">
      <div className="pointer-events-none absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-accent/25 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-48 -right-32 h-[36rem] w-[36rem] rounded-full bg-indigo-500/20 blur-[120px]" />
      <div className="pointer-events-none absolute left-1/2 top-1/3 h-72 w-72 -translate-x-1/2 rounded-full bg-pink-500/10 blur-[100px]" />

      <div className="animate-float-in">
        <img
          src="/frame-finder-logo.png"
          alt="FrameFinder AI logo"
          className="mx-auto h-36 w-auto animate-float drop-shadow-[0_0_45px_rgba(129,140,248,0.55)] sm:h-44"
        />
      </div>

      <h1
        className="mt-8 bg-gradient-to-r from-rose-400 via-indigo-400 to-emerald-400 bg-[length:200%_auto] bg-clip-text text-6xl font-extrabold tracking-tighter text-transparent animate-gradient-flow sm:text-7xl md:text-8xl"
      >
        FrameFinder AI
      </h1>

      <p className="mt-6 max-w-2xl text-lg font-medium leading-relaxed text-slate-300 sm:text-xl md:text-2xl animate-fade-in-up">
        Describe the shot you want and AI finds matching frames from movie
        trailers — <span className="text-glow">camera angles</span>,{' '}
        <span className="text-glow">mood</span>,{' '}
        <span className="text-glow">lighting</span> and all.
      </p>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-3 sm:gap-4 animate-fade-in-up">
        <div className="flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-semibold text-emerald-300 sm:text-base">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400" />
          Search · Browse · Build storyboards
        </div>
      </div>

      <button
        onClick={onEnter}
        className="group mt-12 inline-flex items-center gap-3 rounded-2xl bg-gradient-to-r from-accent via-indigo-500 to-accent-2 bg-[length:200%_auto] px-10 py-5 text-xl font-bold text-white shadow-2xl shadow-accent/40 transition-all duration-300 hover:scale-105 hover:bg-[position:100%_0] hover:shadow-accent/60 active:scale-95 sm:px-12 sm:text-2xl animate-fade-in-up"
      >
        Enter the Studio
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6 transition-transform duration-300 group-hover:translate-x-1.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12l-7.5 7.5M21 12H3" />
        </svg>
      </button>

      <p className="mt-10 text-sm text-slate-500 animate-fade-in-up">
        Powered by CLIP browsing + Gemini understanding
      </p>
    </div>
  )
}