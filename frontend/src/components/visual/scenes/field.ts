// Hero: a living intelligence field. An illustrative concept visual, not market data.
// Layers: a slow structural mesh (the learned baseline), behavioural arcs that morph and occasionally carry a signal,
// tilted orbits (the source streams), sparse pulsing nodes and an atmospheric rim. Every CYCLE seconds the field runs the
// lifecycle STABLE → SIGNAL → LOCAL DISTORTION → ANOMALY → CONTEXT → RISK/EVIDENCE → EQUILIBRIUM: the region under each
// hero label lights in turn and connectors travel between it and a local anomaly. About half of each cycle stays calm.
// The cursor bends and brightens the field where it points and speeds up nearby signals; the idle spin slows while it explores.
import {
  AdditiveBlending, BufferAttribute, BufferGeometry, FrontSide, Group, IcosahedronGeometry, LineLoop, LineSegments, Mesh,
  PerspectiveCamera, Points, Euler, Quaternion, Scene, ShaderMaterial, SphereGeometry, Vector3, Vector4, WireframeGeometry,
} from 'three'
import { COLORS, createRenderer, hash, lineMaterial, pointMaterial, rgb, smooth } from './common'
import type { SceneFactory } from './types'

const CYCLE = 24 // seconds per observation lifecycle
const SPIN = 0.05 // idle rotation (rad/s)
const SEG = 40 // vertices per arc
// Label anchors as fractions of the scene box. Keep in sync with the .hero-layers positions in styles/site.css.
const LABELS = [
  { at: [0.76, 0.12], color: COLORS.green, mobile: true }, // Market behaviour (.layer-a)
  { at: [0.9, 0.37], color: COLORS.cyan, mobile: false }, // News & sentiment (.layer-b)
  { at: [0.14, 0.68], color: COLORS.amber, mobile: false }, // Anomaly detection (.layer-c)
  { at: [0.76, 0.84], color: COLORS.green, mobile: true }, // Risk & evidence (.layer-d)
] as const

// Shared GLSL: uniforms, the object-space field (breathing, local anomaly, cursor bulge) and label/cursor proximity.
const FIELD = `uniform float uTime; uniform vec3 uPulseDir; uniform float uPulse; uniform vec3 uCursor; uniform float uCursorAmt;
  uniform vec3 uAnchors[4]; uniform vec4 uFocus;
  float breath(vec3 p, float t) { return sin(p.x * 2.1 + t * 0.35) * sin(p.y * 2.7 - t * 0.28) * sin(p.z * 1.9 + t * 0.22); }
  float gauss(vec3 a, vec3 b, float k) { float d = distance(a, b); return exp(-d * d * k); }
  vec3 worldDir(vec3 n) { return normalize((modelMatrix * vec4(n, 0.0)).xyz); }
  float facing(vec3 n) { return smoothstep(-0.45, 0.6, normalize(mat3(modelViewMatrix) * n).z); }
  float labelFocus(vec3 w) { return uFocus.x * gauss(w, uAnchors[0], 10.0) + uFocus.y * gauss(w, uAnchors[1], 10.0) + uFocus.z * gauss(w, uAnchors[2], 10.0) + uFocus.w * gauss(w, uAnchors[3], 10.0); }
  vec3 field(vec3 p, out float heat, out float near, out float focus) {
    vec3 n = normalize(p); vec3 w = worldDir(n);
    float d = distance(n, uPulseDir); float local = exp(-d * d * 7.0);
    float ripple = sin(d * 16.0 - uTime * 2.4) * exp(-d * 2.8);
    heat = local * uPulse; near = gauss(w, uCursor, 9.0) * uCursorAmt; focus = labelFocus(w);
    return n * (1.0 + 0.03 * breath(n * 1.6, uTime) + uPulse * (0.16 * local + 0.025 * ripple) + 0.05 * near);
  }`

// Behavioural arcs: great-circle paths lifted off the surface. Each morphs slowly, lights up now and then (about a fifth of
// the time) and carries a signal head; heads run faster near the cursor (uSig is a clock that accelerates there).
const ARC = `attribute vec3 aA; attribute vec3 aB; attribute float aSeed; uniform float uSig;
  vec3 slerpDir(vec3 a, vec3 b, float t) { float o = acos(clamp(dot(a, b), -1.0, 1.0)); return (sin((1.0 - t) * o) * a + sin(t * o) * b) / sin(o); }
  float arcAct() { return smoothstep(0.55, 0.95, sin(uTime * 0.17 + aSeed * 37.0)); }
  float arcHead() { return fract(uSig * 0.22 + aSeed * 5.0) * 1.3 - 0.15; }
  vec3 arcPoint(float t, out float near, out float face) {
    vec3 d = slerpDir(aA, aB, t); near = gauss(worldDir(d), uCursor, 6.0) * uCursorAmt; face = facing(d);
    float lift = (0.08 + 0.12 * fract(aSeed * 7.3)) * (1.0 + 0.35 * sin(uTime * 0.23 + aSeed * 6.28)) + near * 0.12;
    return d * (1.02 + lift * sin(3.14159 * t));
  }`

const bump = (p: number, a: number, b: number) => smooth((p - a) / 0.06) * (1 - smooth((p - (b - 0.06)) / 0.06))
const clamp01 = (x: number) => Math.min(Math.max(x, 0), 1)

function fibonacciSphere(count: number) {
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2, r = Math.sqrt(1 - y * y), phi = i * Math.PI * (3 - Math.sqrt(5))
    positions.set([Math.cos(phi) * r, y, Math.sin(phi) * r], i * 3)
  }
  return positions
}

function randomDir(seed: number) {
  const u = hash(seed) * 2 - 1, a = hash(seed + 0.5) * Math.PI * 2, r = Math.sqrt(1 - u * u)
  return new Vector3(Math.cos(a) * r, u, Math.sin(a) * r)
}

function slerpDir(a: Vector3, b: Vector3, t: number, out: Vector3) {
  const o = Math.acos(Math.min(Math.max(a.dot(b), -1), 1)), s = Math.sin(o)
  if (s < 1e-4) return out.copy(a)
  return out.copy(a).multiplyScalar(Math.sin((1 - t) * o) / s).addScaledVector(b, Math.sin(t * o) / s)
}

/** Rim/core glow shell: opacity follows the view angle (rim) or its inverse (core). */
function shell(radius: number, color: string, opacity: number, power: number, core: boolean) {
  const material = new ShaderMaterial({
    transparent: true, depthWrite: false, blending: AdditiveBlending, side: FrontSide,
    uniforms: { uColor: { value: rgb(color) }, uOpacity: { value: opacity } },
    vertexShader: `varying float vRim; void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vRim = 1.0 - max(dot(normalize(normalMatrix * normal), normalize(-mv.xyz)), 0.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying float vRim;
      void main() { float k = ${core ? '1.0 - vRim' : 'vRim'}; gl_FragColor = vec4(uColor, uOpacity * pow(k, ${power.toFixed(1)})); }`,
  })
  const geometry = new SphereGeometry(radius, 48, 32)
  return { mesh: new Mesh(geometry, material), dispose: () => { geometry.dispose(); material.dispose() } }
}

const create: SceneFactory = (canvas, { lite }) => {
  const renderer = createRenderer(canvas, lite)
  const scene = new Scene()
  const camera = new PerspectiveCamera(35, 1, 0.1, 30)
  const disposables: Array<{ dispose(): void }> = []
  const shared = {
    uTime: { value: 0 }, uSig: { value: 0 }, uPulse: { value: 0 }, uPulseDir: { value: new Vector3(0, 0, 1) },
    uCursor: { value: new Vector3(0, 0, 1) }, uCursorAmt: { value: 0 },
    uAnchors: { value: LABELS.map(() => new Vector3(0, 0, 1)) }, uFocus: { value: new Vector4() },
  }

  const body = new Group()
  scene.add(body)

  // 1. Structural mesh: slow, dim, depth-aware; amber/red only inside the local anomaly.
  const lattice = new WireframeGeometry(new IcosahedronGeometry(1, lite ? 3 : 4))
  const latticeMaterial = new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { ...shared, uBase: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) }, uAlert: { value: rgb(COLORS.amber) }, uRed: { value: rgb(COLORS.red) }, uOpacity: { value: 0.26 } },
    vertexShader: `${FIELD} varying float vHeat; varying float vNear; varying float vFocus; varying float vDepth;
      void main() { float heat, near, focus; vec3 p = field(position, heat, near, focus); vHeat = heat; vNear = near; vFocus = focus;
        vDepth = facing(normalize(position)); gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,
    fragmentShader: `uniform vec3 uBase; uniform vec3 uSignal; uniform vec3 uAlert; uniform vec3 uRed; uniform float uOpacity;
      varying float vHeat; varying float vNear; varying float vFocus; varying float vDepth;
      void main() { vec3 c = mix(uBase, uSignal, clamp(vFocus * 0.9 + vNear, 0.0, 1.0) * 0.85);
        c = mix(c, uAlert, smoothstep(0.1, 0.6, vHeat)); c = mix(c, uRed, smoothstep(0.85, 1.0, vHeat));
        gl_FragColor = vec4(c, uOpacity * (0.16 + 0.84 * vDepth) + (vFocus * 0.22 + vNear * 0.4 + vHeat * 0.5) * (0.3 + 0.7 * vDepth)); }`,
  })
  body.add(new LineSegments(lattice, latticeMaterial))
  disposables.push(lattice, latticeMaterial)

  // Sparse nodes: each twinkles on its own slow interval; brighter near the cursor, a lit label region or the anomaly.
  const nodeGeometry = new BufferGeometry()
  nodeGeometry.setAttribute('position', new BufferAttribute(fibonacciSphere(lite ? 300 : 640), 3))
  const nodeMaterial = pointMaterial(COLORS.green, 2.6, 0.55,
    `float heat, near, focus; p = field(position, heat, near, focus);
     float tw = pow(0.5 + 0.5 * sin(uTime * 0.6 + dot(position, vec3(12.9, 78.2, 37.7))), 14.0);
     glow = (0.28 + tw * 1.3 + heat * 1.6 + near * 1.8 + focus * 0.8) * (0.25 + 0.75 * facing(normalize(position)));`, FIELD)
  Object.assign(nodeMaterial.uniforms, shared)
  body.add(new Points(nodeGeometry, nodeMaterial))
  disposables.push(nodeGeometry, nodeMaterial)

  // 2 + 3. Behavioural arcs with travelling signal heads (one draw call for all arcs, one for all heads).
  const arcCount = lite ? 8 : 18
  const arcA = new Float32Array(arcCount * SEG * 3), arcB = new Float32Array(arcCount * SEG * 3), arcT = new Float32Array(arcCount * SEG), arcS = new Float32Array(arcCount * SEG)
  const headA = new Float32Array(arcCount * 3), headB = new Float32Array(arcCount * 3), headS = new Float32Array(arcCount), arcIndex: number[] = []
  for (let k = 0; k < arcCount; k++) {
    const a = randomDir(k * 3.1 + 1), r = randomDir(k * 3.1 + 2), angle = 0.5 + hash(k * 3.1 + 3) * 0.8
    const perp = r.sub(a.clone().multiplyScalar(r.dot(a))).normalize(), b = a.clone().multiplyScalar(Math.cos(angle)).addScaledVector(perp, Math.sin(angle))
    const seed = hash(k * 7.7 + 0.3)
    headA.set([a.x, a.y, a.z], k * 3); headB.set([b.x, b.y, b.z], k * 3); headS[k] = seed
    for (let i = 0; i < SEG; i++) {
      const n = k * SEG + i
      arcA.set([a.x, a.y, a.z], n * 3); arcB.set([b.x, b.y, b.z], n * 3); arcT[n] = i / (SEG - 1); arcS[n] = seed
      if (i < SEG - 1) arcIndex.push(n, n + 1)
    }
  }
  const arcs = new BufferGeometry()
  arcs.setAttribute('position', new BufferAttribute(new Float32Array(arcCount * SEG * 3), 3))
  arcs.setAttribute('aA', new BufferAttribute(arcA, 3)); arcs.setAttribute('aB', new BufferAttribute(arcB, 3))
  arcs.setAttribute('aT', new BufferAttribute(arcT, 1)); arcs.setAttribute('aSeed', new BufferAttribute(arcS, 1))
  arcs.setIndex(arcIndex)
  const arcMaterial = new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { ...shared, uBase: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) } },
    vertexShader: `${FIELD} ${ARC} attribute float aT; varying float vGlow; varying float vBase; varying float vDepth;
      void main() { float near, face; vec3 p = arcPoint(aT, near, face); float act = arcAct(), head = arcHead();
        float trail = aT <= head ? exp(-(head - aT) * 9.0) : exp(-(aT - head) * 60.0);
        vGlow = act * trail + near * 0.6; vBase = 0.35 + 0.65 * act; vDepth = face; gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,
    fragmentShader: `uniform vec3 uBase; uniform vec3 uSignal; varying float vGlow; varying float vBase; varying float vDepth;
      void main() { gl_FragColor = vec4(mix(uBase, uSignal, clamp(vGlow, 0.0, 1.0)), (0.08 * vBase + vGlow * 0.65) * (0.22 + 0.78 * vDepth)); }`,
  })
  const arcLines = new LineSegments(arcs, arcMaterial)
  arcLines.frustumCulled = false
  body.add(arcLines)
  const heads = new BufferGeometry()
  heads.setAttribute('position', new BufferAttribute(new Float32Array(arcCount * 3), 3))
  heads.setAttribute('aA', new BufferAttribute(headA, 3)); heads.setAttribute('aB', new BufferAttribute(headB, 3)); heads.setAttribute('aSeed', new BufferAttribute(headS, 1))
  const headMaterial = pointMaterial(COLORS.green, 8, 0.9,
    `float head = arcHead(), near, face; p = arcPoint(clamp(head, 0.0, 1.0), near, face);
     glow = arcAct() * step(0.0, head) * step(head, 1.0) * (0.3 + 0.7 * face) * (1.2 + near);`, `${FIELD} ${ARC}`)
  Object.assign(headMaterial.uniforms, shared)
  const headPoints = new Points(heads, headMaterial)
  headPoints.frustumCulled = false
  body.add(headPoints)
  disposables.push(arcs, arcMaterial, heads, headMaterial)

  // 4. Orbits: slow elliptical source streams (market, news, events) that precess around the globe.
  const orbits = [1.3, 1.44, 1.56].slice(0, lite ? 2 : 3).map((radius, index) => {
    const group = new Group()
    const base = { x: 1.2 + index * 0.35, y: index * 0.9, z: 0.3 * index }
    const ring = new BufferGeometry(), points = new Float32Array(192 * 3)
    for (let i = 0; i < 192; i++) { const a = (i / 192) * Math.PI * 2; points.set([Math.cos(a) * radius, Math.sin(a) * radius * 0.86, 0], i * 3) }
    ring.setAttribute('position', new BufferAttribute(points, 3))
    const ringMaterial = lineMaterial(COLORS.grid, 0.2, 3.0, 6.6)
    group.add(new LineLoop(ring, ringMaterial))
    const marker = new BufferGeometry()
    marker.setAttribute('position', new BufferAttribute(new Float32Array(3), 3))
    const markerMaterial = pointMaterial([COLORS.green, COLORS.cyan, COLORS.green][index], 7, 0.85)
    group.add(new Points(marker, markerMaterial))
    scene.add(group)
    disposables.push(ring, ringMaterial, marker, markerMaterial)
    return { group, base, marker, radius, markerMaterial, speed: 0.12 + index * 0.05, offset: index * 2.1, drift: index % 2 ? 1 : -1 }
  })

  // Depth: a faint atmospheric rim and an even fainter inner glow keep the globe predominantly dark.
  const rim = shell(1.1, COLORS.green, lite ? 0.16 : 0.2, 2.6, false), core = shell(0.97, COLORS.green, 0.05, 2.0, true)
  scene.add(rim.mesh, core.mesh)
  disposables.push(rim, core)

  // Cursor field: a soft glow that follows where the cursor points on the sphere.
  const cursorGeometry = new BufferGeometry()
  cursorGeometry.setAttribute('position', new BufferAttribute(new Float32Array(3), 3))
  const cursorMaterial = pointMaterial(COLORS.green, 110, 0)
  scene.add(new Points(cursorGeometry, cursorMaterial))
  disposables.push(cursorGeometry, cursorMaterial)

  // Label anchors (screen-fixed regions under each HTML label) with faint leader lines.
  const anchors = LABELS.map(() => new Vector3(0, 0, 1)), labelPoints = LABELS.map(() => new Vector3())
  const ANOMALY_LABEL = 2, anomalyAnchor = new Vector3(0, 0, 1)
  const leaderGeometry = new BufferGeometry()
  leaderGeometry.setAttribute('position', new BufferAttribute(new Float32Array(LABELS.length * 6), 3))
  leaderGeometry.setAttribute('aT', new BufferAttribute(new Float32Array(LABELS.flatMap(() => [0, 1])), 1))
  leaderGeometry.setAttribute('aL', new BufferAttribute(new Float32Array(LABELS.flatMap((_, i) => [i, i])), 1))
  const leaderMaterial = new ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uFocus: shared.uFocus, uShow: { value: new Vector4(1, 1, 1, 1) }, uColor: { value: rgb(COLORS.line) }, uSignal: { value: rgb(COLORS.green) } },
    vertexShader: `attribute float aT; attribute float aL; uniform vec4 uFocus; uniform vec4 uShow; varying float vT; varying float vF;
      void main() { vT = aT; vec4 f = uFocus * uShow; vF = aL < 0.5 ? f.x : aL < 1.5 ? f.y : aL < 2.5 ? f.z : f.w;
        if ((aL < 0.5 ? uShow.x : aL < 1.5 ? uShow.y : aL < 2.5 ? uShow.z : uShow.w) < 0.5) vF = -1.0;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 uColor; uniform vec3 uSignal; varying float vT; varying float vF;
      void main() { if (vF < 0.0) discard; gl_FragColor = vec4(mix(uColor, uSignal, vF), (0.11 + 0.45 * vF) * mix(1.0, 0.35, vT)); }`,
  })
  scene.add(new LineSegments(leaderGeometry, leaderMaterial))
  const anchorDots = LABELS.map((label) => {
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new BufferAttribute(new Float32Array(3), 3))
    const material = pointMaterial(label.color, 9, 0)
    scene.add(new Points(geometry, material))
    disposables.push(geometry, material)
    return { geometry, material }
  })
  disposables.push(leaderGeometry, leaderMaterial)

  // Lifecycle connectors: market → anomaly (signal), news → anomaly (context), anomaly → risk (evidence).
  const connectors = [[0, -1, COLORS.green], [1, -1, COLORS.cyan], [-1, 3, COLORS.green]].map(([from, to, color]) => {
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new BufferAttribute(new Float32Array(SEG * 3), 3))
    geometry.setAttribute('aT', new BufferAttribute(new Float32Array(Array.from({ length: SEG }, (_, i) => i / (SEG - 1))), 1))
    const material = new ShaderMaterial({
      transparent: true, depthWrite: false,
      uniforms: { uHead: { value: 0 }, uAlpha: { value: 0 }, uColor: { value: rgb(color as string) } },
      vertexShader: 'attribute float aT; varying float vT; void main() { vT = aT; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform float uHead; uniform float uAlpha; uniform vec3 uColor; varying float vT;
        void main() { float trail = vT <= uHead ? exp(-(uHead - vT) * 5.0) : 0.0; gl_FragColor = vec4(uColor, uAlpha * (0.1 + 0.9 * trail)); }`,
    })
    const line = new LineSegments(geometry, material)
    geometry.setIndex(Array.from({ length: SEG - 1 }, (_, i) => [i, i + 1]).flat())
    line.frustumCulled = false
    const dotGeometry = new BufferGeometry()
    dotGeometry.setAttribute('position', new BufferAttribute(new Float32Array(3), 3))
    const dot = pointMaterial(color as string, 10, 0)
    const dotPoints = new Points(dotGeometry, dot)
    dotPoints.frustumCulled = false
    scene.add(line, dotPoints)
    disposables.push(geometry, material, dotGeometry, dot)
    return { from: from as number, to: to as number, geometry, material, dotGeometry, dot }
  })

  // Per-frame state (kept here, never in React).
  const inverse = new Quaternion(), ray = new Vector3(), origin = new Vector3(), aim = new Vector3(), anomaly = new Vector3(), tmp = new Vector3(), a = new Vector3(), b = new Vector3()
  const cursorDir = new Vector3(0, 0, 1), peakEuler = new Euler()
  let lastCycle = -1, last = -1, angle = 0, cursorAmt = 0, labelShow = [1, 1, 1, 1]

  function placeLabels(width: number) {
    const narrow = width < 560 || window.matchMedia('(max-width: 760px)').matches
    labelShow = LABELS.map((label) => (narrow && !label.mobile ? 0 : 1))
    ;(leaderMaterial.uniforms.uShow.value as Vector4).fromArray(labelShow)
    const leader = leaderGeometry.attributes.position as BufferAttribute
    LABELS.forEach((label, i) => {
      const [fx, fy] = label.at
      ray.set(fx * 2 - 1, 1 - fy * 2, 0.5).unproject(camera).sub(camera.position).normalize()
      const L = labelPoints[i].copy(camera.position).addScaledVector(ray, -camera.position.z / ray.z)
      anchors[i].set(L.x, L.y, 1.2).normalize()
      shared.uAnchors.value[i].copy(anchors[i])
      tmp.copy(anchors[i]).multiplyScalar(1.04)
      leader.setXYZ(i * 2, tmp.x, tmp.y, tmp.z); leader.setXYZ(i * 2 + 1, L.x, L.y, L.z)
      ;(anchorDots[i].geometry.attributes.position as BufferAttribute).setXYZ(0, tmp.x, tmp.y, tmp.z)
      anchorDots[i].geometry.attributes.position.needsUpdate = true
    })
    leader.needsUpdate = true
  }

  function drawConnector(c: (typeof connectors)[number], head: number, alpha: number) {
    c.material.uniforms.uAlpha.value = alpha
    c.material.uniforms.uHead.value = head
    if (alpha <= 0.001) { c.dot.uniforms.uOpacity.value = 0; return }
    a.copy(c.from < 0 ? anomaly : anchors[c.from]); b.copy(c.to < 0 ? anomaly : anchors[c.to])
    const position = c.geometry.attributes.position as BufferAttribute
    for (let i = 0; i < SEG; i++) {
      const t = i / (SEG - 1)
      slerpDir(a, b, t, tmp).multiplyScalar(1.03 + 0.22 * Math.sin(Math.PI * t))
      position.setXYZ(i, tmp.x, tmp.y, tmp.z)
    }
    position.needsUpdate = true
    slerpDir(a, b, head, tmp).multiplyScalar(1.03 + 0.22 * Math.sin(Math.PI * head))
    ;(c.dotGeometry.attributes.position as BufferAttribute).setXYZ(0, tmp.x, tmp.y, tmp.z)
    c.dotGeometry.attributes.position.needsUpdate = true
    c.dot.uniforms.uOpacity.value = head > 0 && head < 1 ? alpha : 0
  }

  return {
    staticTime: CYCLE * 0.58, // context and risk lit, no distortion
    resize(width, height, dpr) {
      renderer.setPixelRatio(dpr); renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.position.set(0, 0, camera.aspect < 1 ? 4.9 / Math.max(camera.aspect, 0.62) : 4.9)
      camera.lookAt(0, 0, 0)
      camera.updateProjectionMatrix(); camera.updateMatrixWorld()
      ;[nodeMaterial, headMaterial, cursorMaterial, ...orbits.map((o) => o.markerMaterial), ...anchorDots.map((d) => d.material), ...connectors.map((c) => c.dot)]
        .forEach((m) => { m.uniforms.uDpr.value = dpr })
      placeLabels(width)
    },
    render(time, pointer) {
      // Restart the clocks on the first frame or the reduced-motion still frame; a paused gap (hidden tab) just skips time.
      const reset = last < 0 || time < last
      const dt = reset || time - last > 0.5 ? 0 : time - last
      last = time
      if (reset) { angle = time * SPIN; shared.uSig.value = time }

      // Cursor: where the pointer's ray meets (or passes nearest to) the sphere, eased so the field never snaps.
      origin.copy(camera.position)
      ray.set(pointer.x, -pointer.y, 0.5).unproject(camera).sub(origin).normalize()
      const bDot = origin.dot(ray), disc = bDot * bDot - (origin.lengthSq() - 1)
      let reach = 1
      if (disc > 0) aim.copy(origin).addScaledVector(ray, -bDot - Math.sqrt(disc)).normalize()
      else { aim.copy(origin).addScaledVector(ray, -bDot); reach = 1 - smooth((aim.length() - 1) / 0.7); aim.normalize() }
      cursorDir.lerp(aim, reset ? 1 : 0.12).normalize()
      cursorAmt += (pointer.active * reach - cursorAmt) * (reset ? 1 : 0.08)
      shared.uCursor.value.copy(cursorDir); shared.uCursorAmt.value = cursorAmt
      ;(cursorGeometry.attributes.position as BufferAttribute).setXYZ(0, cursorDir.x * 1.02, cursorDir.y * 1.02, cursorDir.z * 1.02)
      cursorGeometry.attributes.position.needsUpdate = true
      cursorMaterial.uniforms.uOpacity.value = 0.13 * cursorAmt

      // Idle rotation slows while the cursor explores; signals near it run faster.
      angle += dt * SPIN * (1 - 0.65 * cursorAmt)
      shared.uSig.value += dt * (1 + 1.5 * cursorAmt)
      shared.uTime.value = time
      body.rotation.set(0.3 + pointer.y * 0.06, angle + pointer.x * 0.1, 0)
      body.updateMatrixWorld()

      // Lifecycle: stable → signal → local distortion/anomaly → context → risk & evidence → equilibrium (then calm).
      const cycle = Math.floor(time / CYCLE), p = (time % CYCLE) / CYCLE
      if (cycle !== lastCycle) {
        lastCycle = cycle
        // Aim the anomaly so it faces the viewer when it peaks (~0.38 of the cycle), allowing for the spin until then.
        const t = hash(cycle) * Math.PI * 2, peakAngle = angle + SPIN * CYCLE * (0.38 - p)
        inverse.setFromEuler(peakEuler.set(0.3, peakAngle, 0)).invert()
        shared.uPulseDir.value.set(Math.cos(t) * 0.45, Math.sin(t) * 0.35, 0.82).normalize().applyQuaternion(inverse)
      }
      anomaly.copy(shared.uPulseDir.value).applyQuaternion(body.quaternion)
      shared.uPulse.value = smooth((p - 0.28) / 0.08) * (1 - smooth((p - 0.42) / 0.14))
      // The anomaly label's leader glides to the anomaly while it is active, then back to its resting region.
      slerpDir(anchors[ANOMALY_LABEL], anomaly, 0.9 * smooth((p - 0.24) / 0.08) * (1 - smooth((p - 0.5) / 0.12)), anomalyAnchor)
      shared.uAnchors.value[ANOMALY_LABEL].copy(anomalyAnchor)
      tmp.copy(anomalyAnchor).multiplyScalar(1.04)
      ;(leaderGeometry.attributes.position as BufferAttribute).setXYZ(ANOMALY_LABEL * 2, tmp.x, tmp.y, tmp.z)
      leaderGeometry.attributes.position.needsUpdate = true
      ;(anchorDots[ANOMALY_LABEL].geometry.attributes.position as BufferAttribute).setXYZ(0, tmp.x, tmp.y, tmp.z)
      anchorDots[ANOMALY_LABEL].geometry.attributes.position.needsUpdate = true
      const focus = [0.2 + 0.8 * bump(p, 0.05, 0.32), bump(p, 0.36, 0.62), shared.uPulse.value, bump(p, 0.5, 0.72)].map((f, i) => f * labelShow[i])
      shared.uFocus.value.fromArray(focus)
      anchorDots.forEach((d, i) => { d.material.uniforms.uOpacity.value = labelShow[i] * (0.25 + 0.75 * focus[i]) })
      drawConnector(connectors[0], clamp01((p - 0.14) / 0.16), bump(p, 0.14, 0.36) * labelShow[0])
      drawConnector(connectors[1], clamp01((p - 0.38) / 0.14), bump(p, 0.38, 0.62) * labelShow[1])
      drawConnector(connectors[2], clamp01((p - 0.52) / 0.14), bump(p, 0.52, 0.74) * labelShow[3])

      orbits.forEach((o) => {
        o.group.rotation.set(o.base.x + Math.sin(time * 0.05 + o.offset) * 0.08, o.base.y, o.base.z + time * 0.012 * o.drift)
        const t = time * o.speed + o.offset
        o.marker.attributes.position.setXYZ(0, Math.cos(t) * o.radius, Math.sin(t) * o.radius * 0.86, 0)
        o.marker.attributes.position.needsUpdate = true
      })
      renderer.render(scene, camera)
    },
    dispose() { disposables.forEach((d) => d.dispose()); renderer.dispose() },
  }
}

export default create
