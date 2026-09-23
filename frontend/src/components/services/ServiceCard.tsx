import type { Service } from '../../data/services'
export function ServiceCard({service}:{service:Service}){const Icon=service.icon;return <article className="service-card"><span className="service-number">{service.number}</span><Icon className="service-icon" size={25}/><h3>{service.title}</h3><p>{service.description}</p></article>}
