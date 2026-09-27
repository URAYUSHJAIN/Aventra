import { ApiError, apiPost } from './apiClient'

export interface NewsAnalysisRequest { text: string }
export interface NewsAnalysisResult {
  label: 'positive' | 'neutral' | 'negative'
  positive_probability: number
  neutral_probability: number
  negative_probability: number
  sentiment_score: number
  // Additive fields returned by the API since pipeline v0.1.0.
  sentiment?: 'positive' | 'neutral' | 'negative'
  confidence?: number
  model?: string
  model_version?: string | null
  timestamp?: string
  source?: string
}

export async function analyzeNews({ text }: NewsAnalysisRequest): Promise<NewsAnalysisResult> {
  try {
    return await apiPost<NewsAnalysisResult>('/api/news/analyze', { text }, { timeoutMs: 60_000 })
  } catch (error) {
    if (error instanceof ApiError && error.kind === 'client') throw new Error(error.message)
    if (error instanceof ApiError && error.status === 503) throw new Error(error.message)
    if (error instanceof ApiError && (error.kind === 'unavailable' || error.kind === 'timeout')) throw new Error('News analysis service is currently unavailable.')
    throw new Error(error instanceof Error && error.message ? error.message : 'Unable to analyse the text. Please try again.')
  }
}
