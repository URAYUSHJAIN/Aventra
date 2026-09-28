import { ArrowRight } from 'lucide-react'
import { Button } from '../components/common/Button'
import { Scene3D } from '../components/visual/Scene3D'

const APPROACH = [
  ['Signal', 'Detect what changed relative to the instrument’s own behaviour, not a market-wide rule.'],
  ['Context', 'Attach what else happened: linked news, its sentiment, and when it was published relative to the session.'],
  ['Explanation', 'State how unusual it was and which dimensions moved, in plain language with the numbers behind it.'],
  ['Evidence', 'Keep a timestamped chain with provenance, so every flag can be checked rather than trusted.'],
]
const NOT = ['a price predictor', 'a trading bot', 'a buy/sell recommender', 'a portfolio manager', 'a fraud or manipulation detector', 'a fake-news detector']
const PRINCIPLES = [
  ['Real data only', 'Analysis runs only where a permitted provider supplies real observations. Otherwise Aventra says “unavailable” and lists what it tried.'],
  ['Honest scores', 'Thresholds and weights are uncalibrated defaults and are labelled as such. Scores are scores, not probabilities.'],
  ['Association, not causation', 'News is reported as temporally aligned with a session. Aventra never claims an article caused a move.'],
  ['Reproducible research', 'Every reported metric comes from a command in the repository, with its seed, data and limitations written down.'],
]

export function AboutPage() {
  return <main id="main" className="page page-about">
    <header className="wrap about-opening">
      <div className="about-copy">
        <p className="eyebrow">ABOUT AVENTRA</p>
        <h1 className="display-title about-title">Financial data is abundant. <em>Context is not.</em></h1>
        <p className="about-lead">Aventra is an explainable financial-intelligence pipeline that combines adaptive behavioural profiling, anomaly detection, financial-news sentiment and cross-source temporal correlation to contextualise unusual market behaviour.</p>
      </div>
      <div className="about-visual">
        <Scene3D scene="mountain" />
        <p className="visual-caption">Illustrative, not data: a peak that stands out from its own baseline, the kind of deviation Aventra flags.</p>
      </div>
    </header>

    <section className="wrap about-block" aria-labelledby="why-exists">
      <h2 id="why-exists" className="block-label">Why it exists</h2>
      <div className="about-columns">
        <p>Prices, volumes, filings and news all arrive separately. When an instrument moves unusually, the chart shows <em>what</em> happened but not how unusual it was for that asset, or what else was happening at the same moment.</p>
        <p>Aventra investigates one instrument at a time and answers four questions: what happened, how unusual it was, what else happened at the same time, and why it was flagged, with the evidence to check each answer.</p>
      </div>
    </section>

    <section className="wrap about-block" aria-labelledby="approach">
      <h2 id="approach" className="block-label">How it approaches intelligence</h2>
      <ol className="approach">{APPROACH.map(([title, text], i) => <li key={title}><span>{String(i + 1).padStart(2, '0')}</span><strong>{title}</strong><p>{text}</p></li>)}</ol>
    </section>

    <section className="wrap about-block" aria-labelledby="principles">
      <h2 id="principles" className="block-label">Explainability philosophy</h2>
      <dl className="principles">{PRINCIPLES.map(([title, text]) => <div key={title}><dt>{title}</dt><dd>{text}</dd></div>)}</dl>
      <p className="about-not"><span>Aventra is not</span>{NOT.map((n) => <b key={n}>{n}</b>)}</p>
    </section>

    <section className="wrap about-block" aria-labelledby="direction">
      <h2 id="direction" className="block-label">Research direction</h2>
      <div className="about-columns">
        <p>Aventra is a B.Tech final-year research and development project at ABES Engineering College, Ghaziabad. Its open question is whether asset-specific behavioural fingerprints, combined with news context, make unusual-behaviour signals more useful than generic statistical rules.</p>
        <p>The current evaluation measures sensitivity to synthetic anomalies injected into real series; it does not yet answer that question. The methodology, results and limitations are published in full.</p>
      </div>
      <div className="about-actions"><Button href="/research">Read the research <ArrowRight size={15} aria-hidden="true" /></Button><Button href="/intelligence" variant="secondary">Explore Intelligence</Button></div>
    </section>
  </main>
}
