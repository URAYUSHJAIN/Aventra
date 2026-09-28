import { Scene3D } from '../visual/Scene3D'

const SOURCES = ['PRICE', 'NEWS', 'EVENTS', 'VOLUME', 'REPORTS', 'SENTIMENT']
const ANSWERS = [
  ['Unified intelligence', 'Market behaviour, news, sentiment and risk for one instrument, in one place.'],
  ['Behavioural understanding', 'Each instrument is compared with its own learned normal, not a generic rule.'],
  ['Context-rich insights', 'Flagged sessions arrive with the news and events published around them.'],
  ['Explainable risk', 'Every score shows its contributions and the evidence behind them.'],
]

export function WhyAventra() {
  return <section className="section why" id="why-aventra" aria-labelledby="why-title">
    <Scene3D scene="terrain" className="why-terrain" />
    <div className="wrap">
      <div className="why-head">
        <p className="eyebrow">DESIGNED FOR CONTEXT</p>
        <h2 id="why-title" className="display-title why-title">Financial data is abundant. <em>Context is not.</em></h2>
      </div>
      <ol className="problems">
        <li className="problem problem-fragmented reveal"><span className="problem-index">01</span><div><h3>Fragmented data</h3><p>The sources exist, but separately, each in its own format, timezone and place.</p></div>
          <div className="problem-visual fragments" aria-hidden="true">{SOURCES.map((s, i) => <span key={s} style={{ '--i': i } as React.CSSProperties}>{s}</span>)}</div></li>
        <li className="problem problem-context reveal"><span className="problem-index">02</span><div><h3>Lack of context</h3><p>A price moves. The chart shows <em>what</em>. The first question is always the same:</p></div>
          <div className="problem-visual question" aria-hidden="true"><svg viewBox="0 0 200 70"><polyline points="0,20 40,24 80,18 110,22 128,58 160,54 200,56" /></svg><span>But why?</span></div></li>
        <li className="problem problem-overload reveal"><span className="problem-index">03</span><div><h3>Information overload</h3><p>Many streams, little structure. They need to become three things you can reason about.</p></div>
          <div className="problem-visual converge" aria-hidden="true"><svg viewBox="0 0 200 90">{[8, 20, 32, 44, 56, 68, 80].map((y, i) => <path key={y} d={`M0 ${y} C 70 ${y}, 90 ${[18, 45, 72][i % 3]}, 130 ${[18, 45, 72][i % 3]}`} />)}</svg><span className="converge-labels"><b>SIGNAL</b><b>CONTEXT</b><b>EVIDENCE</b></span></div></li>
        <li className="problem problem-risk reveal"><span className="problem-index">04</span><div><h3>Unclear risk</h3><p>Risk is usually a single number with no way to see what produced it.</p></div>
          <div className="problem-visual equation" aria-hidden="true"><span>Market movement</span><i>+</i><span>Behaviour</span><i>+</i><span>News</span><i>+</i><span>Events</span><i>→</i><b>Risk context</b></div></li>
      </ol>
      <div className="answers reveal">
        <p className="eyebrow">HOW AVENTRA ANSWERS</p>
        <ul>{ANSWERS.map(([title, text]) => <li key={title}><h3>{title}</h3><p>{text}</p></li>)}</ul>
      </div>
    </div>
  </section>
}
