import express from 'express'
import cors from 'cors'

const app = express()
app.use(cors())
app.use(express.json())

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://ai-service:8000'

function appendFilterParams(params, key, value) {
  if (!value) return
  const vals = value.split(',')
  vals.forEach(v => params.append(key, v))
}

app.get('/api/search', async (req, res) => {
  const { q, film, camera_angle, shot_size, camera_movement, mood, tone, lighting } = req.query

  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (film) params.set('film', film)
  appendFilterParams(params, 'camera_angle', camera_angle)
  appendFilterParams(params, 'shot_size', shot_size)
  appendFilterParams(params, 'camera_movement', camera_movement)
  appendFilterParams(params, 'mood', mood)
  appendFilterParams(params, 'tone', tone)
  appendFilterParams(params, 'lighting', lighting)

  try {
    const response = await fetch(`${AI_SERVICE_URL}/search?${params.toString()}`)
    const data = await response.json()
    res.json(data)
  } catch (err) {
    console.error('AI service error:', err)
    res.status(500).json({ error: 'Search failed' })
  }
})

app.get('/api/frames', async (req, res) => {
  const { film } = req.query
  let url = `${AI_SERVICE_URL}/frames/all`
  if (film) url += `?film=${encodeURIComponent(film)}`
  try {
    const response = await fetch(url)
    const data = await response.json()
    res.json(data)
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch frames' })
  }
})

app.get('/api/filters', async (req, res) => {
  try {
    const response = await fetch(`${AI_SERVICE_URL}/filters`)
    const data = await response.json()
    res.json(data)
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch filters' })
  }
})

app.get('/api/health', async (req, res) => {
  try {
    const response = await fetch(`${AI_SERVICE_URL}/health`)
    const data = await response.json()
    res.json(data)
  } catch (err) {
    res.status(500).json({ error: 'Health check failed' })
  }
})

app.listen(3001, () => {
  console.log('Backend running on http://localhost:3001')
})
