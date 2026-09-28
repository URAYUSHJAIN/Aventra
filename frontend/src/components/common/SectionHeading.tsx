import type { ReactNode } from 'react'
type Props = { eyebrow?: string; title: ReactNode; intro?: ReactNode; level?: 1 | 2; align?: 'start' | 'center'; id?: string; className?: string }
export function SectionHeading({ eyebrow, title, intro, level = 2, align = 'start', id, className = '' }: Props) { const H = level === 1 ? 'h1' : 'h2'; return <div className={`section-heading align-${align} ${className}`.trim()}>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<H className="display-title" id={id}>{title}</H>{intro && <p className="section-intro">{intro}</p>}</div> }
