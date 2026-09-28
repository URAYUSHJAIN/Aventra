import type { ReactNode } from 'react'
type Props = { children: ReactNode; href?: string; variant?: 'primary' | 'secondary' | 'ghost'; size?: 'md' | 'lg'; className?: string; type?: 'button' | 'submit'; onClick?: () => void; disabled?: boolean }
export function Button({ children, href, variant = 'primary', size = 'md', className = '', type = 'button', onClick, disabled }: Props) {
  const classes = `button button-${variant} button-${size} ${className}`.trim()
  return href ? <a className={classes} href={href} onClick={onClick}>{children}</a> : <button className={classes} type={type} onClick={onClick} disabled={disabled}>{children}</button>
}
