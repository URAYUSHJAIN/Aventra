export interface NewsAnalysisRequest { text: string }
export interface NewsAnalysisResult {
  label: 'positive' | 'neutral' | 'negative'
  positive_probability: number
  neutral_probability: number
  negative_probability: number
  sentiment_score: number
}

interface ApiResponse { success: boolean; data?: NewsAnalysisResult; error?: string }

export async function analyzeNews({ text }: NewsAnalysisRequest): Promise<NewsAnalysisResult> {
  // Empty uses Vite's /api proxy locally; set VITE_API_BASE_URL to the Flask
  // origin in deployment, for example https://api.example.com.
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/news/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
  } catch {
    throw new Error('News analysis service is currently unavailable.')
  }
  const payload = await response.json().catch(() => ({})) as ApiResponse
  if (!response.ok || !payload.success || !payload.data) throw new Error(payload.error ?? 'Unable to analyse the text. Please try again.')
  return payload.data
}
