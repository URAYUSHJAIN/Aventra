import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App'

// Scroll-reveal starting states apply only where they can be undone (IntersectionObserver present, motion allowed).
if (typeof IntersectionObserver !== 'undefined' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) document.documentElement.classList.add('reveal-ready')

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
