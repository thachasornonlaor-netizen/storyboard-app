const API_BASE = import.meta.env.VITE_API_URL || ''
const FRAMES_BASE = import.meta.env.VITE_FRAMES_URL || API_BASE || ''

export function apiUrl(path) {
  if (!path) return path
  return `${API_BASE}${path}`
}

export function frameUrl(path) {
  if (!path) return path
  if (/^https?:\/\//.test(path)) return path
  return `${FRAMES_BASE}${path}`
}