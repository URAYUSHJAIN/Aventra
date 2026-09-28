import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useHealth } from '../../hooks/useHealth'
import { Button } from '../common/Button'
import { GlobalSearch } from '../search/GlobalSearch'
import { Scene3D } from '../visual/Scene3D'

// Example search terms only: selecting one fills the search; no values are shown or implied.
const EXAMPLES = ['RELIANCE', 'AAPL', 'BTC', 'USDINR', 'NIFTY']
const LAYERS = [['Market behaviour', 'layer-a'], ['News & sentiment', 'layer-b'], ['Anomaly detection', 'layer-c'], ['Risk & evidence', 'layer-d']]

export function Hero() {
  const [seed, setSeed] = useState('')
  const health = useHealth()
  const masterSize = health.status === 'ok' ? health.data.instrument_master_size : null
  return <section id="home" className="hero" aria-labelledby="hero-title">
    <div className="wrap hero-grid">
      <div className="hero-copy">
        <p className="eyebrow">FINANCIAL INTELLIGENCE PLATFORM</p>
        <h1 id="hero-title" className="display-title hero-title">Understand what the market is <em>really doing.</em></h1>
        <p className="hero-lead">Aventra brings market behaviour, unusual patterns, financial news, cross-source events, risk and evidence into one explainable intelligence layer.</p>
        <div className="hero-search">
          <GlobalSearch key={seed} size="large" initialQuery={seed} autoFocus={seed !== ''} placeholder="Search any instrument: stocks, funds, forex, crypto…" />
          <div className="hero-examples"><span>Try</span>{EXAMPLES.map((example) => <button type="button" key={example} onClick={() => setSeed(example)} aria-label={`Search for ${example}`}>{example}</button>)}</div>
        </div>
        <div className="hero-actions">
          <Button href="/intelligence" size="lg">Explore Intelligence <ArrowRight size={16} aria-hidden="true" /></Button>
          <Button href="/#how-it-works" variant="ghost" size="lg">How it works</Button>
        </div>
        {masterSize ? <p className="hero-fact"><b>{masterSize.toLocaleString()}</b> instruments in the Instrument Master · analysed only where a permitted provider supplies real data</p>
          : <p className="hero-fact">Analysed only where a permitted provider supplies real data</p>}
      </div>
      <div className="hero-visual">
        <Scene3D scene="field" tracking="section" />
        <ul className="hero-layers" aria-label="Signals Aventra connects">{LAYERS.map(([label, position]) => <li key={label} className={position}><i aria-hidden="true" />{label}</li>)}</ul>
        <p className="visual-caption">Illustrative: a behavioural baseline, a local deviation and a return to equilibrium. Not market data.</p>
      </div>
    </div>
    <a className="scroll-cue" href="#intelligence">Scroll to explore<span aria-hidden="true" /></a>
  </section>
}
