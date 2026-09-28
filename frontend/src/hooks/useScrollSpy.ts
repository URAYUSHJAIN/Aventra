import { useEffect, useState } from 'react'

// Highlights the section currently in view (used by in-page section tabs). No-op where IntersectionObserver is unavailable.
export function useScrollSpy(ids: readonly string[], enabled = true) {
  const [active, setActive] = useState(ids[0] ?? '')
  const key = ids.join('|')
  useEffect(() => {
    if (!enabled || typeof IntersectionObserver === 'undefined') return
    const visible = new Map<string, number>()
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => visible.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0))
      const current = ids.find((id) => (visible.get(id) ?? 0) > 0)
      if (current) setActive(current)
    }, { rootMargin: '-120px 0px -55% 0px', threshold: [0, 0.01, 0.25] })
    ids.forEach((id) => { const el = document.getElementById(id); if (el) observer.observe(el) })
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled])
  return active
}
