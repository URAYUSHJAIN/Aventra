import { ArrowRight } from 'lucide-react'
import { Button } from '../components/common/Button'
import { GlobalSearch } from '../components/search/GlobalSearch'

export function NotFoundPage() {
  return <main id="main" className="page page-404"><section className="wrap not-found"><p className="eyebrow">404 · PAGE NOT FOUND</p><h1 className="display-title">That signal is <em>outside our coverage.</em></h1><p className="section-intro">The page you requested does not exist or may have moved. Search an instrument, or return to the start.</p><GlobalSearch size="large" /><Button href="/">Return home <ArrowRight size={15} aria-hidden="true" /></Button></section></main>
}
