import { useEffect } from 'react'
import { Navbar } from './components/common/Navbar'
import { Footer } from './components/common/Footer'
import { Home } from './pages/Home'
import { NewsAnalysisPage } from './pages/NewsAnalysisPage'
import { CapabilityPage } from './pages/CapabilityPage'
import { IntelligencePage } from './pages/IntelligencePage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const capabilityRoutes = { '/behavioural-fingerprint': 'fingerprint', '/anomaly-detection': 'anomaly', '/event-correlation': 'correlation', '/risk-evidence': 'risk' } as const
  const metadata: Record<string, [string, string]> = {
    '/': ['Aventra | Financial Market Intelligence', 'Aventra provides contextual financial-market intelligence, live market monitoring and FinBERT financial-text sentiment analysis.'],
    '/news-analysis': ['AI Financial News Analysis | Aventra', 'Analyse financial text with Aventra’s FinBERT sentiment-classification pipeline.'],
    '/intelligence': ['Intelligence Dashboard | Aventra', 'Behavioural fingerprint, anomaly detection, news sentiment, cross-source correlation, risk and evidence for a selected asset.'],
    '/behavioural-fingerprint': ['Behavioural Fingerprinting | Aventra', 'Compare an asset’s current behaviour with its adaptive behavioural baseline.'],
    '/anomaly-detection': ['Anomaly Detection | Aventra', 'Statistical, behavioural and Isolation Forest anomaly detection with contributing features.'],
    '/event-correlation': ['Event Correlation | Aventra', 'Market anomalies aligned in time with asset-linked financial news and FinBERT sentiment.'],
    '/risk-evidence': ['Risk & Evidence Chain | Aventra', 'A transparent risk signal with per-component contributions and a timestamped evidence chain.'],
  }
  const [title, description] = metadata[path] ?? ['Page not found | Aventra', 'The requested Aventra page could not be found.']
  useEffect(() => { document.title = title; document.querySelector('meta[name="description"]')?.setAttribute('content', description); document.querySelector('meta[property="og:title"]')?.setAttribute('content', title); document.querySelector('meta[property="og:description"]')?.setAttribute('content', description) }, [title, description])
  const page = path === '/' ? <Home /> : path === '/news-analysis' ? <NewsAnalysisPage /> : path === '/intelligence' ? <IntelligencePage /> : path in capabilityRoutes ? <CapabilityPage capability={capabilityRoutes[path as keyof typeof capabilityRoutes]} /> : <NotFoundPage />
  return <><Navbar />{page}<Footer /></>
}
