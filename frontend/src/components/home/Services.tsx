import { ArrowRight } from 'lucide-react'
import { services } from '../../data/services'
import { SectionHeading } from '../common/SectionHeading'
import { CapabilityVisual } from './CapabilityVisual'

// Five modules with individual editorial treatments (design spec §17), laid out as an asymmetric composition rather than a card grid.
export function Services() {
  return <section className="section capabilities" id="services" aria-labelledby="capabilities-title">
    <div className="wrap">
      <div className="capabilities-head">
        <SectionHeading id="capabilities-title" eyebrow="CAPABILITIES" title={<>Five capabilities. <em>One line of reasoning.</em></>} />
        <p className="section-intro">Each module answers one question and hands its answer to the next, from how an asset normally behaves to why a session was flagged. Diagrams are schematic, not data.</p>
      </div>
      <div className="modules">{services.map((service) => <article key={service.number} id={`service-${service.number}`} className={`module module-${service.visual} reveal`}>
        <div className="module-copy">
          <span className="module-number">{service.number}</span>
          <h3>{service.title}</h3>
          <p className="module-what">{service.description}</p>
          <p className="module-why"><span>Why it matters</span>{service.why}</p>
          <p className="module-flow">→ {service.contributes}</p>
          <a className="text-link" href={service.href}>See it on real data <ArrowRight size={14} aria-hidden="true" /></a>
        </div>
        <div className="module-visual"><CapabilityVisual kind={service.visual} /></div>
      </article>)}</div>
    </div>
  </section>
}
