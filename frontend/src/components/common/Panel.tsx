import type { ReactNode } from 'react'
type Props = { id?: string; eyebrow: string; title: ReactNode; titleId: string; aside?: ReactNode; children: ReactNode; className?: string }
// Shared frame for analytical panels: technical label, heading, optional status on the right.
export function Panel({ id, eyebrow, title, titleId, aside, children, className = '' }: Props) {
  return <section id={id} className={`panel ${className}`.trim()} aria-labelledby={titleId}>
    <header className="panel-head"><div><p className="eyebrow">{eyebrow}</p><h2 id={titleId}>{title}</h2></div>{aside && <div className="panel-aside">{aside}</div>}</header>
    {children}
  </section>
}
