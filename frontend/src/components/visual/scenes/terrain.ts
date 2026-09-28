// Why Aventra / footer: a data terrain made of stacked series ridgelines (a financial data landscape, not mountains).
// Peaks that rise above the surrounding series are lit as signals. The pattern drifts slowly (~20–30 s major cycles).
import { BufferAttribute, BufferGeometry, Group, LineSegments, PerspectiveCamera, Points, Scene, ShaderMaterial } from 'three'
import { COLORS, createRenderer, rgb } from './common'
import type { SceneFactory } from './types'

const WIDTH = 7
const DEPTH = 5

const FIELD = `uniform float uTime; uniform float uAmp; attribute float aK;
  float field(float x, float k, float t) {
    float s = x * 0.9 - t * 0.18;
    float v = sin(s * 1.3 + k * 4.1) * 0.32 + sin(s * 2.6 + k * 9.3 + 1.7) * 0.16 + sin(s * 5.3 + k * 2.3 + t * 0.1) * 0.06;
    float peak = pow(max(0.0, sin(s * 0.55 + k * 3.7 + 1.3)), 8.0) * 0.9;
    return v * 0.45 + peak;
  }`

const create: SceneFactory = (canvas, { lite, variant }) => {
  const footer = variant === 'footer'
  const lines = lite ? 20 : 36, steps = lite ? 90 : 160
  const renderer = createRenderer(canvas, lite)
  const scene = new Scene()
  const camera = new PerspectiveCamera(38, 1, 0.1, 30)
  const group = new Group()
  scene.add(group)

  const positions = new Float32Array(lines * steps * 3), k = new Float32Array(lines * steps), index: number[] = []
  const signalPositions: number[] = [], signalK: number[] = []
  for (let l = 0; l < lines; l++) {
    const z = -DEPTH + (l / (lines - 1)) * DEPTH
    for (let i = 0; i < steps; i++) {
      const x = -WIDTH / 2 + (i / (steps - 1)) * WIDTH, n = l * steps + i
      positions.set([x, 0, z], n * 3); k[n] = l / lines
      if (i < steps - 1) index.push(n, n + 1)
      if (l % 2 === 0 && i % 3 === 0) { signalPositions.push(x, 0, z); signalK.push(l / lines) }
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('aK', new BufferAttribute(k, 1))
  geometry.setIndex(index)
  const uniforms = { uTime: { value: 0 }, uAmp: { value: footer ? 0.5 : 0.85 }, uOpacity: { value: footer ? 0.42 : 0.55 }, uBase: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) }, uDpr: { value: 1 } }
  const lineShader = new ShaderMaterial({
    transparent: true, depthWrite: false, uniforms,
    vertexShader: `${FIELD} varying float vH; varying float vFade;
      void main() { vec3 p = position; float h = field(p.x, aK * 7.0, uTime); p.y = h * uAmp; vH = h;
        vec4 mv = modelViewMatrix * vec4(p, 1.0); vFade = (1.0 - smoothstep(2.0, 7.5, -mv.z)) * (1.0 - smoothstep(0.62, 1.0, abs(position.x) / ${(WIDTH / 2).toFixed(1)}));
        gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uBase; uniform vec3 uSignal; uniform float uOpacity; varying float vH; varying float vFade;
      void main() { vec3 c = mix(uBase, uSignal, smoothstep(0.5, 0.95, vH)); gl_FragColor = vec4(c, uOpacity * vFade * (0.35 + 0.65 * smoothstep(-0.2, 0.9, vH))); }`,
  })
  group.add(new LineSegments(geometry, lineShader))

  const signals = new BufferGeometry()
  signals.setAttribute('position', new BufferAttribute(new Float32Array(signalPositions), 3))
  signals.setAttribute('aK', new BufferAttribute(new Float32Array(signalK), 1))
  const signalShader = new ShaderMaterial({
    transparent: true, depthWrite: false, uniforms,
    vertexShader: `${FIELD} uniform float uDpr; varying float vGlow;
      void main() { vec3 p = position; float h = field(p.x, aK * 7.0, uTime); p.y = h * uAmp; vGlow = smoothstep(0.62, 0.95, h) * (1.0 - smoothstep(0.62, 1.0, abs(position.x) / ${(WIDTH / 2).toFixed(1)}));
        vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_PointSize = 5.0 * uDpr * (2.6 / -mv.z); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uSignal; varying float vGlow;
      void main() { float r = length(gl_PointCoord - 0.5); if (r > 0.5 || vGlow < 0.01) discard; gl_FragColor = vec4(uSignal, vGlow * 0.85 * (1.0 - smoothstep(0.05, 0.5, r))); }`,
  })
  group.add(new Points(signals, signalShader))

  return {
    staticTime: 11,
    resize(width, height, dpr) {
      renderer.setPixelRatio(dpr); renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.position.set(0, footer ? 1.55 : 1.3, footer ? 2.3 : 2.6)
      camera.lookAt(0, footer ? 0 : 0.15, -2.2)
      camera.updateProjectionMatrix()
      // Stretch the landscape so it always reaches both edges on very wide canvases.
      const halfNeeded = Math.tan((camera.fov * Math.PI) / 360) * 4 * camera.aspect
      group.scale.x = Math.max(1, (2 * halfNeeded) / WIDTH)
      uniforms.uDpr.value = dpr
    },
    render(time, pointer) {
      uniforms.uTime.value = time
      group.rotation.y = pointer.x * 0.05
      renderer.render(scene, camera)
    },
    dispose() { geometry.dispose(); signals.dispose(); lineShader.dispose(); signalShader.dispose(); renderer.dispose() },
  }
}

export default create
