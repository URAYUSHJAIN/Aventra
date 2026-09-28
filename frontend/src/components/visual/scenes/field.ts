// Hero: an illustrative behavioural baseline. A stable lattice (the learned "normal"), a signal that locally distorts it,
// an anomaly pulse and a return to equilibrium: the design spec's stable structure → signal → distortion → pulse → equilibrium.
// It is a concept visual, not market data.
import { BufferAttribute, BufferGeometry, Group, IcosahedronGeometry, LineLoop, LineSegments, PerspectiveCamera, Points, Quaternion, Scene, ShaderMaterial, Vector3, WireframeGeometry } from 'three'
import { COLORS, createRenderer, hash, lineMaterial, pointMaterial, rgb, smooth } from './common'
import type { SceneFactory } from './types'

const CYCLE = 14

const DISPLACE = `uniform float uTime; uniform vec3 uPulseDir; uniform float uPulse;
  float breath(vec3 p, float t) { return sin(p.x * 2.1 + t * 0.35) * sin(p.y * 2.7 - t * 0.28) * sin(p.z * 1.9 + t * 0.22); }
  vec3 displace(vec3 p, out float heat) {
    vec3 n = normalize(p); float d = distance(n, uPulseDir); float local = exp(-d * d * 7.0);
    float ripple = sin(d * 16.0 - uTime * 2.4) * exp(-d * 2.8);
    heat = local * uPulse;
    return n * (1.0 + 0.035 * breath(n * 1.6, uTime) + uPulse * (0.2 * local + 0.03 * ripple));
  }`

function envelope(p: number) {
  const a = p < 0.22 ? 0 : p < 0.42 ? 0.55 * smooth((p - 0.22) / 0.2) : p < 0.52 ? 0.55 + 0.45 * smooth((p - 0.42) / 0.1) : Math.exp(-(p - 0.52) * 7.5)
  return a * (1 - smooth((p - 0.9) / 0.1))
}

function fibonacciSphere(count: number, radius: number) {
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2, r = Math.sqrt(1 - y * y), phi = i * Math.PI * (3 - Math.sqrt(5))
    positions.set([Math.cos(phi) * r * radius, y * radius, Math.sin(phi) * r * radius], i * 3)
  }
  return positions
}

const create: SceneFactory = (canvas, { lite }) => {
  const renderer = createRenderer(canvas, lite)
  const scene = new Scene()
  const camera = new PerspectiveCamera(35, 1, 0.1, 30)
  const shared = { uTime: { value: 0 }, uPulse: { value: 0 }, uPulseDir: { value: new Vector3(0, 0, 1) } }

  const body = new Group()
  scene.add(body)
  const lattice = new WireframeGeometry(new IcosahedronGeometry(1, lite ? 3 : 4))
  const latticeMaterial = new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { ...shared, uBase: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) }, uAlert: { value: rgb(COLORS.amber) }, uOpacity: { value: 0.3 } },
    vertexShader: `${DISPLACE} varying float vHeat; varying float vFade;
      void main() { float heat; vec3 p = displace(position, heat); vHeat = heat; vec4 mv = modelViewMatrix * vec4(p, 1.0); vFade = 1.0 - smoothstep(3.6, 5.8, -mv.z); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uBase; uniform vec3 uSignal; uniform vec3 uAlert; uniform float uOpacity; varying float vHeat; varying float vFade;
      void main() { vec3 c = mix(uBase, uSignal, smoothstep(0.05, 0.5, vHeat)); c = mix(c, uAlert, smoothstep(0.6, 0.95, vHeat));
        gl_FragColor = vec4(c, uOpacity * (0.3 + 0.7 * vFade) + vHeat * 0.5); }`,
  })
  body.add(new LineSegments(lattice, latticeMaterial))

  const nodeGeometry = new BufferGeometry()
  nodeGeometry.setAttribute('position', new BufferAttribute(fibonacciSphere(lite ? 520 : 1100, 1), 3))
  const nodeMaterial = pointMaterial(COLORS.green, 2.4, 0.5, 'float heat; p = displace(position, heat); glow = 0.35 + heat * 1.6;', DISPLACE)
  Object.assign(nodeMaterial.uniforms, shared)
  body.add(new Points(nodeGeometry, nodeMaterial))

  // Three source streams (market, news, events) orbiting the baseline, each carrying one slow marker.
  const orbits = [1.42, 1.6, 1.8].map((radius, index) => {
    const group = new Group()
    group.rotation.set(1.2 + index * 0.35, index * 0.9, 0.3 * index)
    const ring = new BufferGeometry()
    const points = new Float32Array(192 * 3)
    for (let i = 0; i < 192; i++) { const a = (i / 192) * Math.PI * 2; points.set([Math.cos(a) * radius, Math.sin(a) * radius, 0], i * 3) }
    ring.setAttribute('position', new BufferAttribute(points, 3))
    const ringMaterial = lineMaterial(COLORS.grid, 0.2, 3.0, 6.6)
    group.add(new LineLoop(ring, ringMaterial))
    const marker = new BufferGeometry()
    marker.setAttribute('position', new BufferAttribute(new Float32Array(3), 3))
    const markerMaterial = pointMaterial(index === 1 ? COLORS.amber : COLORS.green, 7, 0.85)
    group.add(new Points(marker, markerMaterial))
    scene.add(group)
    return { group, marker, radius, markerMaterial, speed: 0.12 + index * 0.05, offset: index * 2.1, dispose: () => { ring.dispose(); marker.dispose(); ringMaterial.dispose(); markerMaterial.dispose() } }
  })

  let lastCycle = -1
  const inverse = new Quaternion()
  return {
    staticTime: CYCLE * 0.5,
    resize(width, height, dpr) {
      renderer.setPixelRatio(dpr); renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.position.set(0, 0, camera.aspect < 1 ? 4.9 / Math.max(camera.aspect, 0.62) : 4.9)
      camera.updateProjectionMatrix()
      nodeMaterial.uniforms.uDpr.value = dpr
      orbits.forEach((o) => { o.markerMaterial.uniforms.uDpr.value = dpr })
    },
    render(time, pointer) {
      const cycle = Math.floor(time / CYCLE)
      if (cycle !== lastCycle) {
        lastCycle = cycle
        const angle = hash(cycle) * Math.PI * 2
        inverse.copy(body.quaternion).invert()
        shared.uPulseDir.value.set(Math.cos(angle) * 0.75, Math.sin(angle) * 0.55, 0.62).normalize().applyQuaternion(inverse)
      }
      shared.uTime.value = time
      shared.uPulse.value = envelope((time % CYCLE) / CYCLE)
      body.rotation.set(0.28 + pointer.y * 0.1, time * 0.03 + pointer.x * 0.18, 0)
      orbits.forEach((o) => {
        const a = time * o.speed + o.offset
        o.marker.attributes.position.setXYZ(0, Math.cos(a) * o.radius, Math.sin(a) * o.radius, 0)
        o.marker.attributes.position.needsUpdate = true
      })
      renderer.render(scene, camera)
    },
    dispose() {
      lattice.dispose(); latticeMaterial.dispose(); nodeGeometry.dispose(); nodeMaterial.dispose()
      orbits.forEach((o) => o.dispose())
      renderer.dispose()
    },
  }
}

export default create
