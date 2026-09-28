import { ArrowUpRight } from 'lucide-react'
import { useScrollSpy } from '../hooks/useScrollSpy'
import { EXPERIMENTS_URL, docUrl } from '../data/project'

// Content summarises docs/05 (as implemented), docs/17 (evaluation) and docs/25 (limitations). Every number is copied from
// experiments/results via docs/17; nothing here is estimated.
const SECTIONS = [
  ['problem', 'Research problem'], ['objective', 'Objective'], ['methodology', 'Methodology'], ['fingerprinting', 'Behavioural fingerprinting'],
  ['anomaly', 'Anomaly detection'], ['news', 'News intelligence'], ['correlation', 'Cross-source correlation'], ['risk', 'Risk & evidence'],
  ['evaluation', 'Evaluation'], ['limitations', 'Limitations'], ['future', 'Future work'],
] as const

const EXP03: Array<[string, number, string, string, string]> = [
  ['Crypto', 5, '0.634 ± 0.100', '0.671 ± 0.096', 'LOF 0.724 ± 0.157; ensemble without Isolation Forest 0.698 ± 0.127'],
  ['Forex', 4, '0.806 ± 0.216', '0.893 ± 0.139', 'Production ensemble highest'],
  ['Mutual funds', 4, '0.883 ± 0.130', '0.917 ± 0.121', 'Production ensemble highest'],
]

export function ResearchPage() {
  const active = useScrollSpy(SECTIONS.map(([id]) => id))
  return <main id="main" className="page page-research">
    <header className="wrap research-opening">
      <p className="eyebrow">RESEARCH &amp; METHODOLOGY</p>
      <h1 className="display-title">A research-first approach to <em>market context.</em></h1>
      <p className="section-intro">What Aventra investigates, how the implemented pipeline works, what has been measured, and what has not. Methods describe the code as it runs today.</p>
    </header>
    <div className="wrap research-grid">
      <nav className="research-toc" aria-label="Research sections"><ol>{SECTIONS.map(([id, label], i) => <li key={id}><a href={`#${id}`} aria-current={active === id ? 'true' : undefined}><span>{String(i + 1).padStart(2, '0')}</span>{label}</a></li>)}</ol></nav>
      <article className="research-body">
        <section id="problem"><h2>Research problem</h2>
          <p>Market data, financial news and events are published by different sources, at different times and in different formats. When an instrument behaves unusually, an analyst must work out by hand whether it is unusual <em>for that instrument</em>, what else happened at the same time, and how much weight the combination deserves.</p></section>
        <section id="objective"><h2>Objective</h2>
          <p>Build an explainable pipeline that, for any instrument with permitted real data, detects behaviour that is unusual relative to the instrument’s own history, attaches temporally aligned news context, and produces a transparent risk signal with a verifiable evidence chain. The open research question is whether asset-specific behavioural fingerprints, combined with news context, improve on generic statistical rules.</p></section>
        <section id="methodology"><h2>Methodology</h2>
          <p>Data comes only from permitted providers, validated against the instrument’s capability profile and aligned to UTC and its own trading sessions. Features use past observations only (no centred windows), and a unit test checks that altering future rows leaves past features unchanged. Detectors are fitted on data before the scored window; experiments use chronological 70/15/15 splits with seed 42.</p></section>
        <section id="fingerprinting"><h2>Behavioural fingerprinting</h2>
          <p>For each dimension (return, volume, volatility, range, gap or drawdown, whichever the data supports), the baseline is the median and MAD × 1.4826 of the previous 120 observations; at least 60 are required, otherwise the status is <code>insufficient_history</code>. The robust z-score maps linearly from |z| = 2 (score 0) to |z| = 6 (score 1). A guarded update clips observations with |z| &gt; 4 before they enter the baseline, so one extreme session cannot redefine normal behaviour.</p></section>
        <section id="anomaly"><h2>Anomaly detection</h2>
          <p>The production score is an ensemble: 0.35 × a statistical z-score, 0.35 × the fingerprint score and 0.30 × an Isolation Forest (200 trees) fitted only on observations before the scoring window. ML scores are mapped to [0, 1] with the empirical distribution of training scores. Severity bands are ≥ 0.85 critical, ≥ 0.65 high (also the flag threshold) and ≥ 0.40 medium. LOF and an LSTM autoencoder are evaluated experimentally only; PELT change points are retrospective context and do not enter detection or risk.</p></section>
        <section id="news"><h2>News intelligence</h2>
          <p>News comes from Alpha Vantage <code>NEWS_SENTIMENT</code> (requires a key; covers US tickers, crypto and forex). Articles are cleaned, de-duplicated and linked to instruments by provider ticker tags or Instrument Master aliases; links below 0.6 confidence are dropped. Sentiment is measured by FinBERT on sentences of up to 64 tokens. Instruments without a permitted news source, including Indian equities, report news as unavailable rather than guessing.</p></section>
        <section id="correlation"><h2>Cross-source correlation</h2>
          <p>For a flagged session, candidate news is news on the same instrument published between 24 h before the open and 12 h after the close. The correlation score is 0.30 × temporal proximity + 0.25 × asset match + 0.20 × |sentiment| + 0.25 × anomaly score. Semantic relevance (all-MiniLM-L6-v2) is reported as a tie-breaker. Results are stated as temporal alignment, never causation.</p></section>
        <section id="risk"><h2>Risk &amp; evidence</h2>
          <p>Risk = 100 × [0.25 × anomaly + 0.20 × fingerprint + anomaly × (0.15 × |sentiment| + 0.20 × correlation + 0.10 × temporal + 0.10 × agreement)]. Context terms are gated by the anomaly score, because without the gate ordinary sessions scored around 48 simply because news existed. Contributions decompose the score exactly. The evidence chain lists every contributing feature, the ensemble, each aligned article with its sentiment and correlation, and the final risk, each with provenance.</p></section>
        <section id="evaluation"><h2>Evaluation</h2>
          <p><strong>EXP-03</strong> injects synthetic anomalies into real multi-asset series (13 keyless instruments, 2021-09-28 to 2026-09-27) and reports results per asset class, never pooled. PR-AUC on the test segments, mean ± standard deviation across instruments:</p>
          <div className="table-scroll"><table className="data-table research-table"><caption className="sr-only">EXP-03 PR-AUC per asset class</caption>
            <thead><tr><th scope="col">Class (instruments)</th><th scope="col">Statistical baseline</th><th scope="col">Production ensemble</th><th scope="col">Best in class</th></tr></thead>
            <tbody>{EXP03.map(([cls, n, b1, b3, best]) => <tr key={cls}><th scope="row">{cls} ({n})</th><td>{b1}</td><td>{b3}</td><td>{best}</td></tr>)}</tbody></table></div>
          <p>Honest reading: the ensemble is <em>not</em> uniformly best (on crypto, LOF and an ablation do better), and at the default threshold it misses most single-day volume and volatility spikes. Standard deviations are large (4–5 instruments, one seed each). Synthetic injections measure sensitivity to designed anomalies, not real-world detection.</p>
          <p><strong>EXP-02</strong> checks the local FinBERT on Financial PhraseBank (Sentences_AllAgree, 2,264 sentences): accuracy 0.9717, macro-F1 0.9625. FinBERT was fine-tuned on this dataset, so these numbers overlap with its training data and are not a generalisation estimate. <strong>EXP-01</strong> is a superseded v0.1 record on Yahoo-era NSE data.</p>
          <p className="research-links"><a href={docUrl('17_MODEL_EVALUATION.md')} target="_blank" rel="noreferrer">Full evaluation <ArrowUpRight size={13} aria-hidden="true" /></a><a href={EXPERIMENTS_URL} target="_blank" rel="noreferrer">Experiment records <ArrowUpRight size={13} aria-hidden="true" /></a></p></section>
        <section id="limitations"><h2>Limitations</h2>
          <ul className="research-list">
            <li>Without provider keys, analysis covers crypto, forex and Indian mutual funds only; equities, ETFs, indices, rates and all news need keys.</li>
            <li>All thresholds and weights are uncalibrated defaults; there is no trained risk model and no SHAP.</li>
            <li>Indian equities have no permitted news source; Alpha Vantage timestamps are assumed to be UTC.</li>
            <li>NSE sessions use the XBOM calendar as a proxy; historical sessions come from observed bars.</li>
            <li>FinBERT: English only, 64-token sentences, unweighted sentence mean, uncalibrated confidence.</li>
            <li>Not yet evaluated: equities, a known-event benchmark, correlation quality and risk calibration.</li>
          </ul>
          <p className="research-links"><a href={docUrl('25_LIMITATIONS.md')} target="_blank" rel="noreferrer">All limitations <ArrowUpRight size={13} aria-hidden="true" /></a></p></section>
        <section id="future"><h2>Future work</h2>
          <ol className="research-list numbered">
            <li>Obtain keys for equities, ETFs and indices, then run EXP-03 on them.</li>
            <li>Calibrate ensemble weights and the flag threshold on validation data per asset class; add multi-day and multi-feature injections and more seeds.</li>
            <li>Refine instrument classification across the full master and measure its accuracy on a labelled sample.</li>
            <li>Find a permitted news source for Indian instruments; hand-label news to measure entity linking.</li>
            <li>Curate a sourced known-event benchmark and evaluate detection lead time.</li>
            <li>Train a risk model with SHAP explanations once labelled outcomes exist.</li>
          </ol></section>
      </article>
    </div>
  </main>
}
