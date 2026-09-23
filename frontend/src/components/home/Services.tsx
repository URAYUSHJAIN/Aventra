import { services } from '../../data/services'
import { SectionHeading } from '../common/SectionHeading'
import { ServiceCard } from '../services/ServiceCard'
export function Services(){return <section className="section services" id="services"><div className="container"><SectionHeading eyebrow="CAPABILITIES" title="Our Services" intro="Five connected capabilities supporting Aventra's financial intelligence workflow."/><div className="services-grid">{services.map(service=><ServiceCard key={service.number} service={service}/>)}</div></div></section>}
