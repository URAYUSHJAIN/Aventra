// Contact: a restrained globe. Nodes are the project's home (Ghaziabad) and the market centres of the permitted providers
// Aventra uses (docs/06): Mumbai (NSE/BSE/AMFI), New York (US listings), Frankfurt (ECB reference rates), St. Louis (FRED).
import { BufferAttribute, BufferGeometry, Group, Line, LineSegments, PerspectiveCamera, Points, Scene, ShaderMaterial, SphereGeometry, Mesh, Vector3 } from 'three'
import { COLORS, createRenderer, lineMaterial, pointMaterial, rgb } from './common'
import type { SceneFactory } from './types'

const HOME: [number, number] = [28.67, 77.45]
const NODES: Array<[number, number]> = [[19.08, 72.88], [40.71, -74.01], [50.11, 8.68], [38.63, -90.2]]
const ARC_CYCLE = 9

function toVector(lat: number, lon: number, radius = 1) {
  const la = (lat * Math.PI) / 180, lo = (lon * Math.PI) / 180
  return new Vector3(Math.cos(la) * Math.sin(lo) * radius, Math.sin(la) * radius, Math.cos(la) * Math.cos(lo) * radius)
}

const create: SceneFactory = (canvas, { lite }) => {
  const renderer = createRenderer(canvas, lite)
  const scene = new Scene()
  const camera = new PerspectiveCamera(35, 1, 0.1, 30)
  const globe = new Group()
  scene.add(globe)
  const disposables: Array<{ dispose(): void }> = []

  const sphere = new SphereGeometry(1, lite ? 40 : 64, lite ? 28 : 44)
  const sphereMaterial = new ShaderMaterial({
    uniforms: { uCore: { value: rgb(COLORS.core) }, uRim: { value: rgb(COLORS.rim) } },
    vertexShader: 'varying vec3 vNormal; varying vec3 vView; void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); vNormal = normalize(normalMatrix * normal); vView = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }',
    fragmentShader: 'uniform vec3 uCore; uniform vec3 uRim; varying vec3 vNormal; varying vec3 vView; void main() { float f = pow(1.0 - max(dot(vNormal, vView), 0.0), 2.4); gl_FragColor = vec4(mix(uCore, uRim, f), 1.0); }',
  })
  globe.add(new Mesh(sphere, sphereMaterial))
  disposables.push(sphere, sphereMaterial)

  // Graticule: parallels every 20°, meridians every 30°.
  const graticule: number[] = []
  const segment = (a: Vector3, b: Vector3) => graticule.push(a.x, a.y, a.z, b.x, b.y, b.z)
  for (let lat = -60; lat <= 60; lat += 20) for (let i = 0; i < 96; i++) segment(toVector(lat, (i / 96) * 360, 1.002), toVector(lat, ((i + 1) / 96) * 360, 1.002))
  for (let lon = 0; lon < 360; lon += 30) for (let i = 0; i < 48; i++) segment(toVector(-80 + (i / 48) * 160, lon, 1.002), toVector(-80 + ((i + 1) / 48) * 160, lon, 1.002))
  const gridGeometry = new BufferGeometry()
  gridGeometry.setAttribute('position', new BufferAttribute(new Float32Array(graticule), 3))
  const gridMaterial = lineMaterial(COLORS.grid, 0.2, 2.4, 3.8)
  gridMaterial.depthTest = true
  globe.add(new LineSegments(gridGeometry, gridMaterial))
  disposables.push(gridGeometry, gridMaterial)

  // Market nodes.
  const nodePositions = [HOME, ...NODES].flatMap(([lat, lon]) => toVector(lat, lon, 1.01).toArray())
  const nodeGeometry = new BufferGeometry()
  nodeGeometry.setAttribute('position', new BufferAttribute(new Float32Array(nodePositions), 3))
  const nodeMaterial = pointMaterial(COLORS.green, 9, 0.9)
  nodeMaterial.depthTest = true
  globe.add(new Points(nodeGeometry, nodeMaterial))
  disposables.push(nodeGeometry, nodeMaterial)

  // Signal arcs from home to each node: a faint path with a short travelling pulse.
  const arcMaterial = new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uTime: { value: 0 }, uColor: { value: rgb(COLORS.green) } },
    vertexShader: 'attribute float aS; attribute float aOffset; varying float vS; varying float vOffset; void main() { vS = aS; vOffset = aOffset; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform float uTime; uniform vec3 uColor; varying float vS; varying float vOffset;
      void main() { float head = fract(uTime / ${ARC_CYCLE.toFixed(1)} + vOffset) * 1.5 - 0.2; float tail = clamp((vS - (head - 0.3)) / 0.3, 0.0, 1.0) * step(vS, head);
        gl_FragColor = vec4(uColor, 0.08 + 0.75 * tail); }`,
  })
  disposables.push(arcMaterial)
  const home = toVector(...HOME)
  NODES.forEach(([lat, lon], index) => {
    const target = toVector(lat, lon), steps = 64
    const positions = new Float32Array((steps + 1) * 3), s = new Float32Array(steps + 1), offset = new Float32Array(steps + 1).fill(index * 0.27)
    for (let i = 0; i <= steps; i++) {
      const t = i / steps
      const point = home.clone().lerp(target, t).normalize().multiplyScalar(1.01 + Math.sin(Math.PI * t) * 0.13 * home.distanceTo(target))
      positions.set(point.toArray(), i * 3); s[i] = t
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new BufferAttribute(positions, 3))
    geometry.setAttribute('aS', new BufferAttribute(s, 1))
    geometry.setAttribute('aOffset', new BufferAttribute(offset, 1))
    globe.add(new Line(geometry, arcMaterial))
    disposables.push(geometry)
  })

  return {
    staticTime: ARC_CYCLE * 0.45,
    resize(width, height, dpr) {
      renderer.setPixelRatio(dpr); renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.position.set(0, 0, camera.aspect < 1 ? 3.9 / Math.max(camera.aspect, 0.6) : 3.9)
      camera.updateProjectionMatrix()
      nodeMaterial.uniforms.uDpr.value = dpr
    },
    render(time, pointer) {
      arcMaterial.uniforms.uTime.value = time
      globe.rotation.set(0.42 + pointer.y * 0.08, -1.2 + time * 0.022 + pointer.x * 0.2, 0)
      renderer.render(scene, camera)
    },
    dispose() { disposables.forEach((d) => d.dispose()); renderer.dispose() },
  }
}

export default create
