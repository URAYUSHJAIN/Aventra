import { AdditiveBlending, NormalBlending, ShaderMaterial, Vector3, WebGLRenderer } from 'three'

// Scene colours are written straight to the sRGB canvas by the shaders (no colour-management conversion), so they match the CSS tokens.
export const COLORS = { green: '#4dff9a', amber: '#f2b64c', red: '#ff6b6b', cyan: '#5cc8f0', line: '#7f958c', grid: '#56645f', core: '#0a0d10', rim: '#1d3a2b' }

export function rgb(hex: string) { return new Vector3(parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255) }

export function createRenderer(canvas: HTMLCanvasElement, lite: boolean) {
  const renderer = new WebGLRenderer({ canvas, alpha: true, antialias: !lite, powerPreference: 'low-power' })
  renderer.setClearColor(0x000000, 0)
  return renderer
}

export const smooth = (x: number) => { const t = Math.min(Math.max(x, 0), 1); return t * t * (3 - 2 * t) }
export const hash = (n: number) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s) }

/** Round, soft points (size in CSS pixels, attenuated with distance). `body` may modify `p` and `glow`. */
export function pointMaterial(color: string, size: number, opacity: number, body = '', header = '') {
  return new ShaderMaterial({
    transparent: true, depthWrite: false, blending: AdditiveBlending,
    uniforms: { uColor: { value: rgb(color) }, uSize: { value: size }, uDpr: { value: 1 }, uOpacity: { value: opacity } },
    vertexShader: `uniform float uSize; uniform float uDpr; varying float vAlpha; ${header}
      void main() { vec3 p = position; float glow = 1.0; ${body} vAlpha = glow; vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_PointSize = uSize * uDpr * (3.2 / -mv.z) * (0.6 + 0.4 * min(glow, 2.0)); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying float vAlpha;
      void main() { float r = length(gl_PointCoord - 0.5); if (r > 0.5) discard; gl_FragColor = vec4(uColor, uOpacity * vAlpha * (1.0 - smoothstep(0.1, 0.5, r))); }`,
  })
}

/** Thin lines that fade with depth, so the front of an object reads brighter than the back. */
export function lineMaterial(color: string, opacity: number, near = 2.4, far = 5.2) {
  return new ShaderMaterial({
    transparent: true, depthWrite: false, blending: NormalBlending,
    uniforms: { uColor: { value: rgb(color) }, uOpacity: { value: opacity } },
    vertexShader: `varying float vFade; void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vFade = 1.0 - smoothstep(${near.toFixed(2)}, ${far.toFixed(2)}, -mv.z); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: 'uniform vec3 uColor; uniform float uOpacity; varying float vFade; void main() { gl_FragColor = vec4(uColor, uOpacity * (0.25 + 0.75 * vFade)); }',
  })
}
