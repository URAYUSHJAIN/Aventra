import { useEffect, useRef, useState } from 'react'
import { FieldFallback, GlobeFallback, MountainFallback, TerrainFallback } from './Fallbacks'
import type { Pointer, SceneHandle } from './scenes/types'

// Lazy-loaded WebGL scenes (three.js is split into its own chunk and never blocks first paint).
const LOADERS = { field: () => import('./scenes/field'), globe: () => import('./scenes/globe'), terrain: () => import('./scenes/terrain'), mountain: () => import('./scenes/mountain') }
const FALLBACKS = { field: FieldFallback, globe: GlobeFallback, terrain: TerrainFallback, mountain: MountainFallback }
export type SceneName = keyof typeof LOADERS

const MAX_DPR = 1.75
let webglSupport: boolean | null = null

function supports3D() {
  if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined' || typeof ResizeObserver === 'undefined') return false
  if (webglSupport === null) {
    try {
      const probe = document.createElement('canvas')
      const context = probe.getContext('webgl2') ?? probe.getContext('webgl')
      webglSupport = !!context
      context?.getExtension('WEBGL_lose_context')?.loseContext()
    } catch { webglSupport = false }
  }
  return webglSupport
}

/**
 * Decorative 3D container. Renders only while on screen and the tab is visible; renders one still frame for
 * prefers-reduced-motion; uses a lighter scene on small or low-core devices; falls back to static SVG without WebGL.
 */
export function Scene3D({ scene, variant, className = '' }: { scene: SceneName; variant?: string; className?: string }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [mode, setMode] = useState<'pending' | 'webgl' | 'fallback'>('pending')

  useEffect(() => {
    const wrap = wrapRef.current, canvas = canvasRef.current
    if (!wrap || !canvas) return
    if (!supports3D()) { setMode('fallback'); return }
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
    const lite = window.matchMedia('(max-width: 700px)').matches || (navigator.hardwareConcurrency ?? 8) <= 4
    let handle: SceneHandle | null = null, raf = 0, visible = false, disposed = false
    const pointer: Pointer = { x: 0, y: 0 }, target: Pointer = { x: 0, y: 0 }
    const start = performance.now()

    const frame = () => {
      raf = 0
      if (!handle) return
      const still = reduced.matches
      pointer.x += (target.x - pointer.x) * 0.04; pointer.y += (target.y - pointer.y) * 0.04
      handle.render(still ? handle.staticTime : (performance.now() - start) / 1000, still ? { x: 0, y: 0 } : pointer)
      if (!still && visible && document.visibilityState === 'visible') raf = requestAnimationFrame(frame)
    }
    const kick = () => { if (!raf && handle && !disposed) raf = requestAnimationFrame(frame) }
    const resize = () => { const box = wrap.getBoundingClientRect(); handle?.resize(Math.max(1, box.width), Math.max(1, box.height), Math.min(window.devicePixelRatio || 1, MAX_DPR)); kick() }
    const onPointer = (event: PointerEvent) => { if (event.pointerType !== 'mouse') return; const box = wrap.getBoundingClientRect(); target.x = ((event.clientX - box.left) / box.width - 0.5) * 2; target.y = ((event.clientY - box.top) / box.height - 0.5) * 2; kick() }
    const onLeave = () => { target.x = 0; target.y = 0 }

    LOADERS[scene]().then((module) => {
      if (disposed) return
      try { handle = module.default(canvas, { lite, variant }); setMode('webgl'); resize() } catch { setMode('fallback') }
    }).catch(() => { if (!disposed) setMode('fallback') })

    const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(wrap)
    const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) kick() }, { rootMargin: '120px' }); visibility.observe(wrap)
    document.addEventListener('visibilitychange', kick)
    reduced.addEventListener('change', kick)
    wrap.addEventListener('pointermove', onPointer)
    wrap.addEventListener('pointerleave', onLeave)
    return () => {
      disposed = true
      cancelAnimationFrame(raf)
      resizeObserver.disconnect(); visibility.disconnect()
      document.removeEventListener('visibilitychange', kick)
      reduced.removeEventListener('change', kick)
      wrap.removeEventListener('pointermove', onPointer)
      wrap.removeEventListener('pointerleave', onLeave)
      handle?.dispose()
    }
  }, [scene, variant])

  const Fallback = FALLBACKS[scene]
  return <div ref={wrapRef} className={`scene3d scene-${scene} is-${mode} ${className}`.trim()} aria-hidden="true">
    <canvas ref={canvasRef} />
    {mode !== 'webgl' && <Fallback />}
  </div>
}
