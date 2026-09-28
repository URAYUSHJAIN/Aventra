// About page: a single data summit. A wireframe massif whose highest ridges turn green, one signal at the peak and a
// slow contour scan climbing from base to summit (~16 s), a gentle rise and fall and outward ripples. Illustrative only:
// it shows no market data.
import { BufferAttribute, BufferGeometry, Group, LineSegments, PerspectiveCamera, Points, Scene, ShaderMaterial } from 'three'
import { COLORS, createRenderer, pointMaterial, rgb } from './common'
import type { SceneFactory } from './types'

const SIZE = 2.6 // half-width of the square grid; the rim fades out so the massif reads as an island
const SCAN = 16 // seconds for one contour scan from base to summit
const SWAY = 36 // seconds for one slow left–right sway of the massif

/** Height at (x, z): one main peak with radiating ridges, a lower shoulder and gentle surface texture. */
function height(x: number, z: number) {
  const r = Math.hypot(x, z * 1.15)
  const massif = Math.exp(-r * r * 0.55)
  const ridges = 1 - Math.abs(Math.sin(Math.atan2(z, x) * 3 + r * 1.7))
  const shoulder = Math.exp(-((x - 1.05) ** 2 + (z + 0.55) ** 2) * 1.9) * 0.42
  const texture = Math.sin(x * 2.3 + 1.1) * Math.sin(z * 2.9 + 0.4) * 0.07 + Math.sin(x * 5.1 - z * 4.3) * 0.03
  return Math.max(0, massif * (1.25 + 0.3 * ridges * Math.min(1, r)) + shoulder + texture * (0.3 + massif))
}

const create: SceneFactory = (canvas, { lite }) => {
  const n = lite ? 46 : 80
  const renderer = createRenderer(canvas, lite)
  const scene = new Scene()
  const camera = new PerspectiveCamera(34, 1, 0.1, 40)
  const group = new Group()
  scene.add(group)

  const positions = new Float32Array(n * n * 3), index: number[] = []
  let top = 0, peak = [0, 0, 0]
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = -SIZE + (2 * SIZE * i) / (n - 1), z = -SIZE + (2 * SIZE * j) / (n - 1), y = height(x, z)
      positions.set([x, y, z], (j * n + i) * 3)
      if (y > top) { top = y; peak = [x, y, z] }
    }
  }
  for (let j = 0; j < n; j++) for (let i = 0; i < n - 1; i++) index.push(j * n + i, j * n + i + 1) // ridgelines along x
  for (let i = 0; i < n; i += 2) for (let j = 0; j < n - 1; j++) index.push(j * n + i, (j + 1) * n + i) // sparser cross lines
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setIndex(index)

  // Motion shared by the wireframe and the summit: the massif rises and falls (~11 s) and ripples roll outward over its base.
  const MOTION = `uniform float uTime;
    vec3 moved(vec3 p) { float r = length(p.xz); float edge = 1.0 - smoothstep(0.6, 1.0, r / ${SIZE.toFixed(1)});
      p.y = p.y * (1.0 + 0.14 * sin(uTime * 0.55)) + sin(r * 3.2 - uTime * 1.3) * 0.06 * smoothstep(0.1, 1.2, r) * edge; return p; }`
  const uniforms = { uTime: { value: 0 }, uTop: { value: top }, uScan: { value: 0 }, uOpacity: { value: lite ? 0.5 : 0.42 }, uBase: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) } }
  const lineShader = new ShaderMaterial({
    transparent: true, depthWrite: false, uniforms,
    vertexShader: `${MOTION} uniform float uTop; varying float vH; varying float vFade;
      void main() { vH = position.y / uTop; float r = length(position.xz) / ${SIZE.toFixed(1)};
        vec4 mv = modelViewMatrix * vec4(moved(position), 1.0); vFade = (1.0 - smoothstep(0.62, 1.0, r)) * (1.0 - 0.55 * smoothstep(5.0, 9.0, -mv.z));
        gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uBase; uniform vec3 uSignal; uniform float uOpacity; uniform float uScan; varying float vH; varying float vFade;
      void main() { float band = exp(-pow((vH - uScan) / 0.04, 2.0)) * smoothstep(0.02, 0.12, uScan);
        vec3 c = mix(uBase, uSignal, max(smoothstep(0.72, 0.98, vH), band));
        gl_FragColor = vec4(c, min(1.0, vFade * (uOpacity * (0.28 + 0.72 * smoothstep(0.0, 0.6, vH)) + band * 0.6))); }`,
  })
  group.add(new LineSegments(geometry, lineShader))

  const summit = new BufferGeometry()
  summit.setAttribute('position', new BufferAttribute(new Float32Array([peak[0], peak[1] + 0.03, peak[2]]), 3))
  const dot = pointMaterial(COLORS.green, 16, 0.95, 'p = moved(p);', MOTION), halo = pointMaterial(COLORS.green, 64, 0.16, 'p = moved(p);', MOTION)
  dot.uniforms.uTime = halo.uniforms.uTime = uniforms.uTime
  group.add(new Points(summit, halo), new Points(summit, dot))

  return {
    staticTime: 9,
    resize(width, heightPx, dpr) {
      renderer.setPixelRatio(dpr); renderer.setSize(width, heightPx, false)
      camera.aspect = width / heightPx
      camera.position.set(0, 2.5, 6.6)
      camera.lookAt(0, 0.5, 0)
      camera.updateProjectionMatrix()
      dot.uniforms.uDpr.value = dpr; halo.uniforms.uDpr.value = dpr
    },
    render(time, pointer) {
      uniforms.uTime.value = time
      uniforms.uScan.value = ((time / SCAN) % 1) * 1.1
      halo.uniforms.uOpacity.value = 0.12 + 0.16 * (0.5 + 0.5 * Math.sin((time * Math.PI * 2) / 4))
      group.rotation.y = 0.5 + Math.sin((time * Math.PI * 2) / SWAY) * 0.45 + pointer.x * 0.12
      group.rotation.x = pointer.y * 0.03
      renderer.render(scene, camera)
    },
    dispose() { geometry.dispose(); summit.dispose(); lineShader.dispose(); dot.dispose(); halo.dispose(); renderer.dispose() },
  }
}

export default create
