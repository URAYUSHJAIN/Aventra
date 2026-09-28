import { ArrowRight, ChevronDown, Menu, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { services } from '../../data/services'
import { GlobalSearch } from '../search/GlobalSearch'
import { Button } from './Button'
import { Logo } from './Logo'

const links = [{ label: 'Intelligence', href: '/intelligence' }, { label: 'Research', href: '/research' }, { label: 'Docs', href: '/doc' }, { label: 'About', href: '/about' }, { label: 'Contact', href: '/contact' }]
const CAPABILITY_PATHS = services.map((s) => s.href)

export function Navbar() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const [open, setOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const sheetRef = useRef<HTMLDivElement>(null)

  useEffect(() => { const onScroll = () => setScrolled(window.scrollY > 8); onScroll(); window.addEventListener('scroll', onScroll, { passive: true }); return () => window.removeEventListener('scroll', onScroll) }, [])
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMenuOpen(false); setOpen(false) } }
    const onClick = (event: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false) }
    document.addEventListener('keydown', onKey); document.addEventListener('mousedown', onClick)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onClick) }
  }, [])
  useEffect(() => {
    document.body.classList.toggle('nav-locked', open)
    if (open) sheetRef.current?.querySelector<HTMLElement>('a, button, input')?.focus()
    return () => document.body.classList.remove('nav-locked')
  }, [open])

  const current = (href: string) => (href === path ? 'page' : undefined)
  const close = () => { setOpen(false); setMenuOpen(false) }
  return <><header className={`site-nav${scrolled ? ' is-scrolled' : ''}`}>
    <nav className="nav-bar" aria-label="Main navigation">
      <Logo />
      <div className="nav-links">
        <a href={links[0].href} aria-current={current(links[0].href)}>{links[0].label}</a>
        <div className="nav-menu" ref={menuRef}>
          <button type="button" className={CAPABILITY_PATHS.includes(path) ? 'is-current' : ''} onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen} aria-controls="capabilities-menu">Capabilities <ChevronDown size={14} aria-hidden="true" className={menuOpen ? 'rotated' : ''} /></button>
          <div id="capabilities-menu" className={`nav-dropdown${menuOpen ? ' is-open' : ''}`}>
            {services.map((s) => <a href={s.href} key={s.number} aria-current={current(s.href)} onClick={close}><span>{s.number}</span><strong>{s.title}</strong><small>{s.contributes}</small></a>)}
            <a className="nav-dropdown-all" href="/#services" onClick={close}>How the five connect <ArrowRight size={13} aria-hidden="true" /></a>
          </div>
        </div>
        {links.slice(1).map((l) => <a href={l.href} key={l.label} aria-current={current(l.href)}>{l.label}</a>)}
      </div>
      <div className="nav-actions">
        <div className="nav-search"><GlobalSearch compact placeholder="Search instruments…" /></div>
        <a className="icon-link nav-search-link" href="/intelligence" aria-label="Search instruments"><Search size={17} aria-hidden="true" /></a>
        <Button href="/intelligence" className="nav-cta">Explore Intelligence</Button>
        <button type="button" className="menu-toggle" onClick={() => setOpen(!open)} aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} aria-controls="mobile-nav">{open ? <X size={20} /> : <Menu size={20} />}</button>
      </div>
    </nav>
  </header>
    <div id="mobile-nav" ref={sheetRef} className={`nav-sheet${open ? ' is-open' : ''}`} hidden={!open}>
      <GlobalSearch placeholder="Search any instrument…" />
      <ol className="sheet-links">{links.map((l, i) => <li key={l.label}><a href={l.href} aria-current={current(l.href)} onClick={close}><span>{String(i + 1).padStart(2, '0')}</span>{l.label}</a></li>)}</ol>
      <p className="eyebrow">CAPABILITIES</p>
      <ul className="sheet-capabilities">{services.map((s) => <li key={s.number}><a href={s.href} onClick={close}><span>{s.number}</span>{s.title}</a></li>)}</ul>
      <Button href="/intelligence" size="lg" onClick={close}>Explore Intelligence <ArrowRight size={16} aria-hidden="true" /></Button>
    </div>
  </>
}
