import { useEffect } from 'react'
import { Navbar } from './components/common/Navbar'
import { Footer } from './components/common/Footer'
import { Home } from './pages/Home'
import { NewsAnalysisPage } from './pages/NewsAnalysisPage'
import { CapabilityDemoPage } from './pages/CapabilityDemoPage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const capabilityRoutes = { '/behavioural-fingerprint': 'fingerprint', '/anomaly-detection': 'anomaly', '/event-correlation': 'correlation', '/risk-evidence': 'risk' } as const
  const metadata: Record<string, [string, string]> = {
    '/': ['Aventra | Financial Market Intelligence', 'Aventra provides contextual financial-market intelligence, live market monitoring and FinBERT financial-text sentiment analysis.'],
    '/news-analysis': ['AI Financial News Analysis | Aventra', 'Analyse financial text with Aventra’s FinBERT sentiment-classification pipeline.'],
    '/behavioural-fingerprint': ['Behavioural Fingerprinting | Aventra', 'Explore Aventra’s adaptive behavioural fingerprinting workspace.'],
    '/anomaly-detection': ['Anomaly Detection | Aventra', 'Explore Aventra’s multi-source anomaly detection workspace.'],
    '/event-correlation': ['Event Correlation | Aventra', 'Explore Aventra’s cross-source event correlation workspace.'],
    '/risk-evidence': ['Risk & Evidence Chain | Aventra', 'Explore Aventra’s explainable risk and evidence-chain workspace.'],
  }
  const [title, description] = metadata[path] ?? ['Page not found | Aventra', 'The requested Aventra page could not be found.']
  useEffect(() => { document.title = title; document.querySelector('meta[name="description"]')?.setAttribute('content', description); document.querySelector('meta[property="og:title"]')?.setAttribute('content', title); document.querySelector('meta[property="og:description"]')?.setAttribute('content', description) }, [title, description])
  const page = path === '/' ? <Home /> : path === '/news-analysis' ? <NewsAnalysisPage /> : path in capabilityRoutes ? <CapabilityDemoPage capability={capabilityRoutes[path as keyof typeof capabilityRoutes]} /> : <NotFoundPage />
  return <><Navbar />{page}<Footer /></>
}
