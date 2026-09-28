import { ExternalLink } from 'lucide-react'
import { services } from '../../data/services'
import { REPOSITORY_URL, docUrl } from '../../data/project'
import { useHealth } from '../../hooks/useHealth'
import { Scene3D } from '../visual/Scene3D'
import { Logo } from './Logo'

function ApiStatus() {
  const health = useHealth()
  const [tone, text] = health.status === 'loading' ? ['neutral', 'Checking API…'] : health.status === 'unreachable' ? ['negative', 'API unreachable'] : health.data.status === 'ok' ? ['positive', `API online · pipeline v${health.data.pipeline_version}`] : ['warning', 'API degraded']
  return <span className={`api-status tone-${tone}`} role="status"><i aria-hidden="true" />{text}</span>
}

export function Footer() {
  return <footer className="site-footer">
    <Scene3D scene="terrain" variant="footer" className="footer-terrain" />
    <div className="wrap footer-grid">
      <div className="footer-brand">
        <Logo />
        <p className="footer-tagline">Detect hidden patterns.<br />Understand market risk.</p>
        <p className="footer-copy">An explainable financial-intelligence pipeline connecting market behaviour, news and risk with evidence.</p>
      </div>
      <nav className="footer-nav" aria-label="Footer navigation">
        <div><p className="eyebrow">PRODUCT</p><a href="/intelligence">Intelligence</a><a href="/#market">Watchlist monitor</a><a href="/news-analysis">Text sentiment</a><a href="/#how-it-works">How it works</a></div>
        <div><p className="eyebrow">CAPABILITIES</p>{services.map((s) => <a key={s.number} href={s.href}>{s.title}</a>)}</div>
        <div><p className="eyebrow">PROJECT</p><a href="/about">About</a><a href="/research">Research</a><a href="/doc">Documentation</a><a href="/contact">Contact</a></div>
        <div><p className="eyebrow">RESOURCES</p><a href={REPOSITORY_URL} target="_blank" rel="noreferrer">Source code <ExternalLink size={11} aria-hidden="true" /></a><a href={docUrl('14_API_SPECIFICATION.md')} target="_blank" rel="noreferrer">API specification <ExternalLink size={11} aria-hidden="true" /></a><a href={docUrl('25_LIMITATIONS.md')} target="_blank" rel="noreferrer">Limitations <ExternalLink size={11} aria-hidden="true" /></a></div>
      </nav>
    </div>
    <div className="wrap footer-bottom">
      <span>© {new Date().getFullYear()} Aventra · B.Tech research project, ABES Engineering College</span>
      <span className="footer-disclaimer">Analytical signals, not financial advice or predictions.</span>
      <ApiStatus />
    </div>
  </footer>
}
