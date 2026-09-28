import { useEffect } from 'react'
import { Navbar } from './components/common/Navbar'
import { Footer } from './components/common/Footer'
import { Home } from './pages/Home'
import { NewsAnalysisPage } from './pages/NewsAnalysisPage'
import { CapabilityPage } from './pages/CapabilityPage'
import { IntelligencePage } from './pages/IntelligencePage'
import { AboutPage } from './pages/AboutPage'
import { ResearchPage } from './pages/ResearchPage'
import { DocPage } from './pages/DocPage'
import { ContactPage } from './pages/ContactPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { useRevealAll } from './hooks/useReveal'

// Home-page anchors that became pages keep working (bookmarks, old links).
const LEGACY_ANCHORS: Record<string, string> = { '#about': '/about', '#contact': '/contact' }

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const legacy = path === '/' ? LEGACY_ANCHORS[window.location.hash] : undefined
  const capabilityRoutes = { '/behavioural-fingerprint': 'fingerprint', '/anomaly-detection': 'anomaly', '/event-correlation': 'correlation', '/risk-evidence': 'risk' } as const
  const metadata: Record<string, [string, string]> = {
    '/': ['Aventra | Financial Market Intelligence', 'Understand what the market is really doing: behaviour, unusual patterns, news, cross-source events, risk and evidence in one explainable view.'],
    '/news-analysis': ['News Intelligence · Text Sentiment | Aventra', 'Measure the sentiment of financial text: a contextual signal, not a market prediction.'],
    '/intelligence': ['Intelligence | Aventra', 'Behavioural fingerprint, anomaly detection, news sentiment, cross-source correlation, risk and evidence for a selected instrument.'],
    '/behavioural-fingerprint': ['Behavioural Fingerprinting | Aventra', 'Compare an asset’s current behaviour with its adaptive behavioural baseline.'],
    '/anomaly-detection': ['Anomaly Detection | Aventra', 'Statistical, behavioural and Isolation Forest anomaly detection with contributing features.'],
    '/event-correlation': ['Cross-Source Correlation | Aventra', 'Market anomalies aligned in time with asset-linked financial news and sentiment.'],
    '/risk-evidence': ['Explainable Risk & Evidence | Aventra', 'A transparent risk signal with per-component contributions and a timestamped evidence chain.'],
    '/about': ['About | Aventra', 'Financial data is abundant. Context is not. What Aventra is, why it exists and how it approaches explainable market intelligence.'],
    '/research': ['Research & Methodology | Aventra', 'Research problem, methodology, evaluation, limitations and future work of the Aventra project.'],
    '/doc': ['Documentation | Aventra', 'Aventra publications and engineering documentation.'],
    '/contact': ['Contact | Aventra', 'Get in touch with the Aventra team at ABES Engineering College.'],
  }
  const [title, description] = metadata[path] ?? ['Page not found | Aventra', 'The requested Aventra page could not be found.']
  useRevealAll()
  useEffect(() => { if (legacy) window.location.replace(legacy) }, [legacy])
  useEffect(() => { document.title = title; document.querySelector('meta[name="description"]')?.setAttribute('content', description); document.querySelector('meta[property="og:title"]')?.setAttribute('content', title); document.querySelector('meta[property="og:description"]')?.setAttribute('content', description) }, [title, description])
  const pages: Record<string, () => React.ReactNode> = { '/': () => <Home />, '/news-analysis': () => <NewsAnalysisPage />, '/intelligence': () => <IntelligencePage />, '/about': () => <AboutPage />, '/research': () => <ResearchPage />, '/doc': () => <DocPage />, '/contact': () => <ContactPage /> }
  const page = path in capabilityRoutes ? <CapabilityPage capability={capabilityRoutes[path as keyof typeof capabilityRoutes]} /> : pages[path]?.() ?? <NotFoundPage />
  return <><a className="skip-link" href="#main">Skip to content</a><Navbar />{page}<Footer /></>
}
