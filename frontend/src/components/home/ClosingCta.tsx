import { ArrowRight } from 'lucide-react'
import { Button } from '../common/Button'
import { GlobalSearch } from '../search/GlobalSearch'

export function ClosingCta() {
  return <section className="closing" aria-labelledby="closing-title">
    <div className="wrap closing-inner">
      <div>
        <p className="eyebrow">READY TO INVESTIGATE</p>
        <h2 id="closing-title" className="display-title">From fragmented signals to <em>one explainable view.</em></h2>
      </div>
      <div className="closing-actions">
        <GlobalSearch size="large" placeholder="Search an instrument to begin…" />
        <Button href="/intelligence" size="lg">Explore Intelligence <ArrowRight size={16} aria-hidden="true" /></Button>
      </div>
    </div>
  </section>
}
