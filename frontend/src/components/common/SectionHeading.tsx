type Props = { eyebrow?: string; title: string; intro?: string }
export function SectionHeading({ eyebrow, title, intro }: Props) { return <div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2 className="section-title">{title}</h2>{intro && <p className="section-intro">{intro}</p>}</div> }
