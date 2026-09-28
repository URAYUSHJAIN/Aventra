import { useEffect } from 'react'

// Adds `is-visible` to static `.reveal` blocks as they scroll into view. The hidden starting state only applies under
// `html.reveal-ready` (set in main.tsx when IntersectionObserver exists and motion is allowed), so content never stays hidden.
export function useRevealAll() {
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target) } }), { rootMargin: '0px 0px -8% 0px' })
    document.querySelectorAll('.reveal').forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])
}
