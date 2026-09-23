import { Menu, Search, X } from 'lucide-react'
import { useState } from 'react'
import shortLogo from '../../assets/short-logo.png'
import { Button } from './Button'
const links = [{ label:'Home',href:'#home' },{ label:'About Us',href:'#about' },{ label:'Services',href:'#services' },{ label:'Contact',href:'#contact' }]
export function Navbar() { const [open,setOpen]=useState(false); const close=()=>setOpen(false); return <nav className="nav" aria-label="Main navigation"><a href="#home" className="brand-logo" aria-label="Aventra home"><img src={shortLogo} alt="Aventra" /></a><div className={`nav-links ${open?'open':''}`}>{links.map(l=><a href={l.href} onClick={close} key={l.label}>{l.label}</a>)}</div><div className="nav-actions"><button className="nav-search" aria-label="Search"><Search size={18}/></button><Button href="#contact">Get Started</Button><button className="menu-toggle" onClick={()=>setOpen(!open)} aria-label={open?'Close navigation':'Open navigation'} aria-expanded={open}>{open?<X/>:<Menu/>}</button></div></nav> }
