import type { ReactNode } from 'react'
type Props = { children: ReactNode; href?: string; variant?: 'primary' | 'secondary'; className?: string }
export function Button({ children, href, variant = 'primary', className = '' }: Props) {
  const classes = `button button-${variant} ${className}`
  return href ? <a className={classes} href={href}>{children}</a> : <button className={classes} type="button">{children}</button>
}
