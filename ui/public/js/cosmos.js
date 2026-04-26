// ============================================================================
// cosmos.js — Three.js starfield + nebula + aurora
// ============================================================================

const REDUCED_MOTION = window.matchMedia?.(
  "(prefers-reduced-motion: reduce)",
).matches;

export function startCosmos() {
  if (typeof THREE === "undefined") {
    console.warn("THREE not loaded");
    return null;
  }
  const canvas = document.getElementById("cosmos");
  if (!canvas) return null;

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: true,
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);
  resize();

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(65, 1, 0.1, 1000);
  camera.position.z = 5;

  // ---- Starfield (3 layers) ------------------------------------------------
  const stars = makeStarfield(8000);
  scene.add(stars.points);

  // ---- Nebula clouds -------------------------------------------------------
  const nebula = makeNebula();
  scene.add(nebula);

  // ---- Aurora veil ---------------------------------------------------------
  const aurora = makeAurora();
  scene.add(aurora);

  // ---- Particle stream emitter (logs/avatar reactions) --------------------
  const particles = makeParticles();
  scene.add(particles.points);

  // ---- Mouse parallax ------------------------------------------------------
  const mouse = { tx: 0, ty: 0, x: 0, y: 0 };
  window.addEventListener("mousemove", (e) => {
    mouse.tx = e.clientX / window.innerWidth - 0.5;
    mouse.ty = e.clientY / window.innerHeight - 0.5;
  });

  window.addEventListener("resize", resize);

  function resize() {
    const w = window.innerWidth,
      h = window.innerHeight;
    renderer.setSize(w, h, false);
    if (camera) {
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }

  let t = 0;
  renderer.setAnimationLoop(() => {
    if (REDUCED_MOTION) {
      // Render once and bail out of continuous animation cost
      renderer.render(scene, camera);
      renderer.setAnimationLoop(null);
      return;
    }
    t += 1 / 60;

    mouse.x += (mouse.tx - mouse.x) * 0.04;
    mouse.y += (mouse.ty - mouse.y) * 0.04;

    stars.points.rotation.y = mouse.x * 0.06;
    stars.points.rotation.x = mouse.y * 0.06;
    stars.points.material.uniforms.uTime.value = t;

    nebula.rotation.z = t * 0.005;

    aurora.material.uniforms.uTime.value = t;

    particles.update(t);

    renderer.render(scene, camera);
  });

  return { renderer, scene, camera, particles, dispose };

  function dispose() {
    renderer.setAnimationLoop(null);
    renderer.dispose();
  }
}

// ----------------------------------------------------------------------------
// Starfield with twinkle shader
// ----------------------------------------------------------------------------
function makeStarfield(count) {
  const geom = new THREE.BufferGeometry();
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  const tints = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    // Distribute on a sphere shell
    const r = 30 + Math.random() * 40;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);

    const c = Math.random();
    sizes[i] = c < 0.85 ? 0.5 + Math.random() * 1.0 : 1.2 + Math.random() * 1.4;
    phases[i] = Math.random() * Math.PI * 2;
    tints[i] = Math.random();
  }

  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geom.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geom.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
  geom.setAttribute("aTint", new THREE.BufferAttribute(tints, 1));

  const material = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    },
    vertexShader: `
      attribute float aSize;
      attribute float aPhase;
      attribute float aTint;
      uniform float uTime;
      uniform float uPixelRatio;
      varying float vTwinkle;
      varying float vTint;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        float twinkle = 0.55 + 0.45 * sin(uTime * 1.3 + aPhase);
        vTwinkle = twinkle;
        vTint = aTint;
        gl_PointSize = aSize * uPixelRatio * (240.0 / -mv.z) * (0.6 + 0.4 * twinkle);
      }
    `,
    fragmentShader: `
      varying float vTwinkle;
      varying float vTint;
      void main() {
        vec2 d = gl_PointCoord - 0.5;
        float r = length(d);
        if (r > 0.5) discard;
        float a = pow(1.0 - r * 2.0, 1.6);
        vec3 cool = vec3(0.78, 0.88, 1.0);
        vec3 warm = vec3(1.0, 0.86, 0.82);
        vec3 color = mix(cool, warm, vTint * 0.4);
        gl_FragColor = vec4(color, a * vTwinkle * 0.95);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });

  return { points: new THREE.Points(geom, material), material };
}

// ----------------------------------------------------------------------------
// Nebula — soft volumetric points clouds
// ----------------------------------------------------------------------------
function makeNebula() {
  const group = new THREE.Group();
  const colors = [
    new THREE.Color(0x5b21b6),
    new THREE.Color(0x312e81),
    new THREE.Color(0x701a75),
    new THREE.Color(0x0e7490),
    new THREE.Color(0x6b21a8),
    new THREE.Color(0x1e3a8a),
  ];
  for (let n = 0; n < 6; n++) {
    const count = 800;
    const geom = new THREE.BufferGeometry();
    const pos = new Float32Array(count * 3);
    const cx = (Math.random() - 0.5) * 30;
    const cy = (Math.random() - 0.5) * 16;
    const cz = -10 - Math.random() * 25;
    const radius = 10 + Math.random() * 12;
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.pow(Math.random(), 0.6) * radius;
      pos[i * 3] = cx + Math.cos(a) * r + (Math.random() - 0.5) * 4;
      pos[i * 3 + 1] = cy + Math.sin(a) * r * 0.45 + (Math.random() - 0.5) * 4;
      pos[i * 3 + 2] = cz + (Math.random() - 0.5) * 8;
    }
    geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      color: colors[n % colors.length],
      size: 1.4 + Math.random() * 1.2,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.1 + Math.random() * 0.06,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    group.add(new THREE.Points(geom, mat));
  }
  return group;
}

// ----------------------------------------------------------------------------
// Aurora — bottom shader veil
// ----------------------------------------------------------------------------
function makeAurora() {
  const geom = new THREE.PlaneGeometry(60, 18, 60, 16);
  const mat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      uniform float uTime;
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vec3 p = position;
        p.z += sin(p.x * 0.3 + uTime * 0.6) * 0.6 +
               cos(p.y * 0.4 + uTime * 0.4) * 0.4;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      varying vec2 vUv;
      void main() {
        float t = uTime * 0.12;
        vec3 cyan = vec3(0.0, 0.96, 1.0);
        vec3 violet = vec3(0.55, 0.36, 0.96);
        vec3 magenta = vec3(1.0, 0.18, 0.79);
        float k = sin(vUv.x * 3.0 + t) * 0.5 + 0.5;
        vec3 color = mix(violet, cyan, k);
        color = mix(color, magenta, sin(t + vUv.y * 4.0) * 0.5 + 0.5);
        float alpha = smoothstep(0.0, 0.3, vUv.y) * (1.0 - smoothstep(0.6, 1.0, vUv.y));
        gl_FragColor = vec4(color, alpha * 0.10);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(0, -7, -5);
  mesh.rotation.x = -0.4;
  return mesh;
}

// ----------------------------------------------------------------------------
// Particles — pooled, recycled, emitted on events
// ----------------------------------------------------------------------------
function makeParticles() {
  const max = 400;
  const geom = new THREE.BufferGeometry();
  const positions = new Float32Array(max * 3);
  const velocities = new Float32Array(max * 3);
  const lives = new Float32Array(max); // remaining seconds; 0 = dead
  const tints = new Float32Array(max);

  for (let i = 0; i < max; i++) lives[i] = 0;

  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geom.setAttribute("aTint", new THREE.BufferAttribute(tints, 1));

  const material = new THREE.PointsMaterial({
    color: 0x00f5ff,
    size: 0.18,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });

  const points = new THREE.Points(geom, material);

  let lastT = 0;
  function update(t) {
    const dt = Math.min(0.05, t - lastT);
    lastT = t;
    const pos = geom.attributes.position.array;
    for (let i = 0; i < max; i++) {
      if (lives[i] <= 0) continue;
      pos[i * 3 + 0] += velocities[i * 3 + 0] * dt;
      pos[i * 3 + 1] += velocities[i * 3 + 1] * dt;
      pos[i * 3 + 2] += velocities[i * 3 + 2] * dt;
      lives[i] -= dt;
    }
    geom.attributes.position.needsUpdate = true;
  }

  function emit(origin, target, count = 4) {
    for (let n = 0; n < count; n++) {
      let idx = -1;
      for (let i = 0; i < max; i++) {
        if (lives[i] <= 0) {
          idx = i;
          break;
        }
      }
      if (idx === -1) return;
      positions[idx * 3 + 0] = origin.x + (Math.random() - 0.5) * 0.3;
      positions[idx * 3 + 1] = origin.y + (Math.random() - 0.5) * 0.3;
      positions[idx * 3 + 2] = origin.z;
      const dx = target.x - origin.x,
        dy = target.y - origin.y,
        dz = target.z - origin.z;
      const len = Math.hypot(dx, dy, dz) || 1;
      const speed = 6 + Math.random() * 4;
      velocities[idx * 3 + 0] = (dx / len) * speed;
      velocities[idx * 3 + 1] = (dy / len) * speed;
      velocities[idx * 3 + 2] = (dz / len) * speed;
      lives[idx] = 0.7 + Math.random() * 0.6;
    }
    geom.attributes.position.needsUpdate = true;
  }

  return { points, update, emit };
}
