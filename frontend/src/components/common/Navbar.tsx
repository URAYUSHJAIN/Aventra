import { ChevronDown, Menu, X } from 'lucide-react'
import { useState } from 'react'
import shortLogo from '../../assets/short-logo.png'
import { Button } from './Button'
import { services } from '../../data/services'

const links = [{ label:'Home',href:'/#home' },{ label:'About Us',href:'/#about' },{ label:'Contact',href:'/#contact' }]

export function Navbar() {
  const [open,setOpen]=useState(false); const [servicesOpen,setServicesOpen]=useState(false)
  const close=()=>{setOpen(false);setServicesOpen(false)}
  return <nav className="nav" aria-label="Main navigation"><a href="/" className="brand-logo" aria-label="Aventra home"><img src={shortLogo} alt="Aventra" /></a><div className={`nav-links ${open?'open':''}`}>{links.slice(0,2).map(l=><a href={l.href} onClick={close} key={l.label}>{l.label}</a>)}<div className="services-menu"><button type="button" className="services-toggle" onClick={()=>setServicesOpen(!servicesOpen)} aria-expanded={servicesOpen} aria-controls="services-dropdown">Services <ChevronDown size={14} className={servicesOpen?'rotated':''}/></button><div id="services-dropdown" className={`services-dropdown ${servicesOpen?'visible':''}`}>{services.map(service=><a href={service.href??`/#service-${service.number}`} onClick={close} key={service.number}><span>{service.number}</span>{service.title}</a>)}</div></div>{links.slice(2).map(l=><a href={l.href} onClick={close} key={l.label}>{l.label}</a>)}</div><div className="nav-actions"><Button href="/#contact">Get Started</Button><button className="menu-toggle" onClick={()=>{setOpen(!open);setServicesOpen(false)}} aria-label={open?'Close navigation':'Open navigation'} aria-expanded={open}>{open?<X/>:<Menu/>}</button></div></nav>
}
