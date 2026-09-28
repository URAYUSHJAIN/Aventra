import { ArrowUpRight, FileText, Landmark, ScrollText } from 'lucide-react'
import { ENGINEERING_DOCS, EXPERIMENTS_URL, REPOSITORY_URL, docUrl } from '../data/project'

// No patent, research paper or review paper has been published yet, so all three are marked Coming Soon (design spec §21).
const PUBLICATIONS = [
  { kind: 'PATENT', title: 'Patent', text: 'Patent documentation will be linked here if and when it is filed and made public.', icon: Landmark },
  { kind: 'RESEARCH PAPER', title: 'Research paper', text: 'The project’s research paper will be linked here once it is available.', icon: ScrollText },
  { kind: 'REVIEW PAPER', title: 'Review paper', text: 'The project’s review paper will be linked here once it is available.', icon: FileText },
]

export function DocPage() {
  return <main id="main" className="page page-doc">
    <header className="wrap doc-opening">
      <p className="eyebrow">DOCUMENTATION</p>
      <h1 className="display-title">Documentation &amp; <em>research.</em></h1>
      <p className="section-intro">Publications for the Aventra project, and the engineering documentation that describes the system exactly as it is implemented.</p>
    </header>
    <section className="wrap" aria-labelledby="publications-title">
      <h2 id="publications-title" className="sr-only">Publications</h2>
      <ul className="publications">{PUBLICATIONS.map(({ kind, title, text, icon: Icon }, i) => <li key={kind} className="publication" style={{ '--i': i } as React.CSSProperties}>
        <div className="publication-card">
          <span className="publication-kind">{kind}</span>
          <Icon size={26} aria-hidden="true" />
          <h3>{title}</h3>
          <p>{text}</p>
          <span className="coming-soon">Coming Soon</span>
        </div>
      </li>)}</ul>
    </section>
    <section className="wrap doc-engineering" aria-labelledby="engineering-title">
      <div className="doc-engineering-head"><h2 id="engineering-title" className="display-title small">Engineering documentation</h2><p className="section-intro">Maintained with the code in the public repository.</p></div>
      <ul className="doc-list">{ENGINEERING_DOCS.map((doc) => <li key={doc.file}><a href={docUrl(doc.file)} target="_blank" rel="noreferrer"><span className="doc-file">{doc.file.slice(0, 2)}</span><div><strong>{doc.title}</strong><p>{doc.summary}</p></div><ArrowUpRight size={16} aria-hidden="true" /></a></li>)}
        <li><a href={EXPERIMENTS_URL} target="_blank" rel="noreferrer"><span className="doc-file">EX</span><div><strong>Experiment records</strong><p>EXP-01 to EXP-03 results as JSON and Markdown, with commands and seeds.</p></div><ArrowUpRight size={16} aria-hidden="true" /></a></li>
        <li><a href={REPOSITORY_URL} target="_blank" rel="noreferrer"><span className="doc-file">GH</span><div><strong>Source repository</strong><p>The full code: ML pipeline, Flask API and this frontend.</p></div><ArrowUpRight size={16} aria-hidden="true" /></a></li>
      </ul>
    </section>
  </main>
}
