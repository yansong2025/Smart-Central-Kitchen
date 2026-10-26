// Detailed 3D models for the digital twins, built from three.js shapes (no model files).
//
// twin/__init__.py joins this file in front of kitchen.js. kitchen.js calls
// createModels() once per scene and gets back the materials, a builder for each
// kind of zone, the two robots, people, and small helpers.
//
// Every builder gets (zone, group, front): the zone's data from Python, the group
// to add meshes to (centred on the zone), and `front` (+1 or -1), the side facing
// the corridor. It returns the parts kitchen.js animates: `height` (for the label),
// `glow` (materials that pulse red in an alert; the first is tinted by the
// temperature layer), and anchors for fault effects such as `top` and `doorway`.

function createModels(THREE, RoundedBoxGeometry) {
  // ---- Materials ---------------------------------------------------------------
  const std = (color, metalness = 0.05, roughness = 0.7, extra = {}) =>
    new THREE.MeshStandardMaterial({ color, metalness, roughness, ...extra });
  const glowing = (color, intensity = 1) =>
    new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, toneMapped: false });

  const M = {
    steel: std(0xc6ccd4, 0.9, 0.28),
    brushed: std(0xaab2bc, 0.85, 0.4),
    aluminium: std(0xd6dbe1, 0.7, 0.35),
    darkSteel: std(0x4a515c, 0.7, 0.35),
    black: std(0x1f2228, 0.3, 0.5),
    rubber: std(0x17191d, 0, 0.85),
    glass: std(0xbcd6ea, 0.1, 0.05, { transparent: true, opacity: 0.25, depthWrite: false }),
    pvc: std(0xcfe6f5, 0, 0.2, { transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide }),
    cardboard: std(0xc29a6b, 0, 0.9),
    tape: std(0xe5cc9f, 0, 0.6),
    pallet: std(0xc59c6c, 0, 0.85),
    yellow: std(0xf0b429, 0.1, 0.5),
    red: std(0xd92d20, 0.1, 0.45),
    blueCrate: std(0x2e6fbe, 0, 0.6),
    insulated: std(0x1f5fa8, 0.05, 0.5),
    dough: std(0xfbf4e6, 0, 0.55),
    filling: std(0xc98b6b, 0, 0.7),
    duck: std(0x9a4e1c, 0.15, 0.35),
    cloth: std(0xfbf9f4, 0, 0.85),
    basket: std(0xd2a86e, 0, 0.75),
    basketLid: std(0xb88d55, 0, 0.75),
    white: std(0xf4f5f6, 0, 0.6),
    board: std(0xeef0ea, 0, 0.6),
    skin: std(0xe2b693, 0, 0.7),
    chef: std(0xf7f7f4, 0, 0.8),
    techCoat: std(0x1e3a6b, 0, 0.75),
    trousers: std(0x2b3038, 0, 0.8),
    chair: std(0x7a4f2e, 0, 0.55),
    teal: std(0x0e9384, 0.2, 0.45),
    blue: std(0x2e90fa, 0.2, 0.45),
    warmLight: glowing(0xff9a4a, 1.4),
    ledWhite: glowing(0xeaf4ff, 1.6),
  };

  // ---- Shape helpers -----------------------------------------------------------------
  function add(geometry, mat, x, y, z, parent, cast = true) {
    const mesh = new THREE.Mesh(geometry, mat);
    mesh.position.set(x, y, z);
    mesh.castShadow = cast;
    mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }
  const box = (w, h, d, mat, x, y, z, parent) => add(new THREE.BoxGeometry(w, h, d), mat, x, y, z, parent);
  const rbox = (w, h, d, r, mat, x, y, z, parent) => add(new RoundedBoxGeometry(w, h, d, 3, r), mat, x, y, z, parent);
  const cyl = (top, bottom, h, mat, x, y, z, parent, segments = 24) =>
    add(new THREE.CylinderGeometry(top, bottom, h, segments), mat, x, y, z, parent);
  const ball = (r, mat, x, y, z, parent) => add(new THREE.SphereGeometry(r, 20, 14), mat, x, y, z, parent);
  const capsule = (r, length, mat, x, y, z, parent) => add(new THREE.CapsuleGeometry(r, length, 4, 12), mat, x, y, z, parent);
  const facing = (front) => (front > 0 ? 0 : Math.PI); // rotation that turns a plane toward the corridor

  // A soft dark blob under objects, so they sit on the floor instead of floating.
  const blobCanvas = document.createElement("canvas");
  blobCanvas.width = blobCanvas.height = 128;
  const blobPen = blobCanvas.getContext("2d");
  const blobGradient = blobPen.createRadialGradient(64, 64, 10, 64, 64, 64);
  blobGradient.addColorStop(0, "rgba(16,24,40,0.5)");
  blobGradient.addColorStop(1, "rgba(16,24,40,0)");
  blobPen.fillStyle = blobGradient;
  blobPen.fillRect(0, 0, 128, 128);
  const blobTexture = new THREE.CanvasTexture(blobCanvas);
  function contactShadow(w, d, parent, x = 0, z = 0) {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(w, d),
      new THREE.MeshBasicMaterial({ map: blobTexture, transparent: true, depthWrite: false, toneMapped: false }),
    );
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(x, 0.07, z);
    mesh.renderOrder = 1;
    parent.add(mesh);
    return mesh;
  }

  // A small screen whose picture is drawn on a canvas. Returns redraw(...args).
  function screen(w, h, parent, x, y, z, rotationY, draw) {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = Math.round((256 * h) / w);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const mesh = add(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: texture, toneMapped: false }), x, y, z, parent, false);
    mesh.rotation.y = rotationY;
    let shown = null;
    const redraw = (...args) => {
      const key = JSON.stringify(args);
      if (key === shown) return;
      shown = key;
      draw(canvas.getContext("2d"), canvas.width, canvas.height, ...args);
      texture.needsUpdate = true;
    };
    redraw();
    return redraw;
  }

  // Screen pictures.
  function drawReading(pen, w, h, text = "--", alert = false) {
    pen.fillStyle = "#0b1220";
    pen.fillRect(0, 0, w, h);
    pen.fillStyle = alert ? "#ff6b5e" : "#5ee08a";
    pen.font = `700 ${Math.round(h * 0.55)}px Inter, system-ui, sans-serif`;
    pen.textAlign = "center";
    pen.textBaseline = "middle";
    pen.fillText(text, w / 2, h / 2 + 2, w - 16);
  }
  function drawPanel(pen, w, h, title = "", value = "", alert = false) {
    pen.fillStyle = alert ? "#3a0d0a" : "#0c2440";
    pen.fillRect(0, 0, w, h);
    pen.fillStyle = alert ? "#ff6b5e" : "#7cc4ff";
    pen.font = `600 ${Math.round(h * 0.18)}px Inter, system-ui, sans-serif`;
    pen.fillText(title, 14, h * 0.28);
    pen.fillStyle = "#ffffff";
    pen.font = `700 ${Math.round(h * 0.32)}px Inter, system-ui, sans-serif`;
    pen.fillText(value, 14, h * 0.7, w - 28);
    pen.fillStyle = alert ? "#ff6b5e" : "#5ee08a";
    pen.fillRect(14, h * 0.82, (w - 28) * (alert ? 0.25 : 0.85), 6);
  }
  function drawCameraFeed(pen, w, h, text = "", alert = false) {
    pen.fillStyle = "#101418";
    pen.fillRect(0, 0, w, h);
    pen.fillStyle = "#2a2f36";
    pen.fillRect(0, h * 0.35, w, h * 0.4); // the belt
    for (let i = 0; i < 4; i++) {
      const x = 30 + i * ((w - 60) / 3);
      const bad = alert && i % 2 === 0;
      pen.fillStyle = "#f6efe0";
      pen.beginPath();
      pen.ellipse(x, h * 0.55, 18, 13, 0, 0, Math.PI * 2);
      pen.fill();
      pen.strokeStyle = bad ? "#ff4d40" : "#4ade80";
      pen.lineWidth = 3;
      pen.strokeRect(x - 26, h * 0.55 - 21, 52, 42);
    }
    pen.fillStyle = alert ? "#ff6b5e" : "#4ade80";
    pen.font = `700 ${Math.round(h * 0.16)}px Inter, system-ui, sans-serif`;
    pen.fillText(text, 12, h * 0.2);
  }

  // A three-light signal tower (andon): green while running, red flashing on a fault.
  function andonTower(parent, x, y, z) {
    const tower = new THREE.Group();
    tower.position.set(x, y, z);
    parent.add(tower);
    cyl(0.025, 0.025, 0.35, M.darkSteel, 0, 0.175, 0, tower);
    const lights = [0x17b26a, 0xf79009, 0xd92d20].map((color, i) => {
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.1, transparent: true, opacity: 0.92, toneMapped: false });
      cyl(0.075, 0.075, 0.12, mat, 0, 0.42 + i * 0.13, 0, tower);
      return mat;
    });
    cyl(0.07, 0.075, 0.04, M.black, 0, 0.8, 0, tower);
    const [green, amber, red] = lights;
    return (time, fault) => {
      green.emissiveIntensity = fault ? 0.08 : 1.8;
      amber.emissiveIntensity = 0.08;
      red.emissiveIntensity = fault ? (Math.sin(time * 10) > 0 ? 3 : 0.15) : 0.08;
    };
  }

  // A conveyor along x: frame, legs, belt and end rollers. The belt top is at y = 0.98.
  function conveyor(parent, centreX, length) {
    const start = centreX - length / 2, end = centreX + length / 2;
    rbox(length, 0.05, 0.66, 0.02, M.rubber, centreX, 0.955, 0, parent);
    for (const z of [-0.36, 0.36]) {
      box(length, 0.1, 0.04, M.steel, centreX, 0.93, z, parent);
      box(length, 0.04, 0.04, M.steel, centreX, 0.25, z * 0.92, parent);
      for (const x of [start + 0.15, centreX, end - 0.15]) box(0.05, 0.9, 0.05, M.steel, x, 0.45, z * 0.92, parent);
    }
    for (const x of [start, end]) cyl(0.05, 0.05, 0.7, M.brushed, x, 0.955, 0, parent).rotation.x = Math.PI / 2;
  }

  // A wooden pallet, 1 m square, top surface at y = 0.15.
  function pallet(parent, x, z) {
    const g = new THREE.Group();
    g.position.set(x, 0, z);
    parent.add(g);
    for (let i = 0; i < 5; i++) box(1.0, 0.025, 0.15, M.pallet, 0, 0.14, -0.42 + i * 0.21, g);
    for (const bx of [-0.42, 0, 0.42]) for (const bz of [-0.42, 0, 0.42]) box(0.12, 0.09, 0.12, M.pallet, bx, 0.08, bz, g);
    for (const bz of [-0.42, 0.42]) box(1.0, 0.025, 0.12, M.pallet, 0, 0.015, bz, g);
    return g;
  }
  // A taped cardboard box, sitting on y.
  function carton(parent, w, h, d, x, y, z, mat = M.cardboard) {
    box(w, h, d, mat, x, y + h / 2, z, parent);
    box(w + 0.005, 0.005, 0.07, M.tape, x, y + h + 0.002, z, parent);
  }

  // ---- People ---------------------------------------------------------------------------
  // A kitchen worker, about 1.8 m tall, facing +z. role: "chef" (whites and a chef's hat)
  // or "tech" (a navy maintenance technician in a yellow hard hat).
  function person(parent, x, z, rotationY = 0, role = "chef") {
    const tech = role === "tech";
    const coat = tech ? M.techCoat : M.chef;
    const p = new THREE.Group();
    p.position.set(x, 0, z);
    p.rotation.y = rotationY;
    parent.add(p);
    const legs = [-0.09, 0.09].map((s) => capsule(0.075, 0.55, M.trousers, s, 0.36, 0, p));
    capsule(0.2, 0.42, coat, 0, 1.05, 0, p);
    if (tech) box(0.42, 0.05, 0.02, M.yellow, 0, 1.12, 0.2, p); // hi-vis stripe
    else box(0.34, 0.5, 0.02, M.white, 0, 0.92, 0.19, p); // apron
    const arms = [-1, 1].map((s) => {
      const arm = capsule(0.06, 0.42, coat, s * 0.25, 1.08, 0.04, p);
      arm.rotation.z = s * 0.12;
      return arm;
    });
    ball(0.13, M.skin, 0, 1.6, 0, p);
    if (tech) {
      add(new THREE.SphereGeometry(0.16, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), M.yellow, 0, 1.66, 0, p); // hard hat
      cyl(0.2, 0.2, 0.02, M.yellow, 0, 1.66, 0.02, p);
      box(0.22, 0.16, 0.1, M.darkSteel, 0.27, 0.7, 0.05, p); // toolbox in hand
    } else {
      cyl(0.12, 0.13, 0.16, M.white, 0, 1.76, 0, p); // chef's hat
      ball(0.15, M.white, 0, 1.86, 0, p).scale.set(1, 0.6, 1);
    }
    contactShadow(0.7, 0.7, p);
    return { group: p, legs, arms };
  }
  // A seated dining guest (torso and head), on a chair facing the table centre.
  function guest(parent, coatColor) {
    const g = new THREE.Group();
    parent.add(g);
    capsule(0.18, 0.3, std(coatColor, 0, 0.8), 0, 0.82, 0, g);
    ball(0.13, M.skin, 0, 1.27, 0, g);
    ball(0.135, std(0x2b2118, 0, 0.9), 0.02, 1.31, 0, g).scale.set(1, 0.75, 1); // hair
    return g;
  }

  // ---- Zone builders ---------------------------------------------------------------------
  const builders = {
    // A walk-in chiller or freezer: insulated panels, a heavy door, strip curtain,
    // a live temperature display beside the door and a condensing unit on the roof.
    cold_room(zone, group, front) {
      const freezer = zone.name.startsWith("Freezer");
      const W = zone.w - 0.5, D = zone.d - 0.6, H = 2.6;
      const faceZ = (front * D) / 2;
      const body = std(freezer ? 0xe7eff7 : 0xf2f4f6, 0.05, 0.4);
      rbox(W, H, D, 0.05, body, 0, H / 2, 0, group);
      for (let x = -W / 2 + 0.52; x < W / 2 - 0.2; x += 0.52) {
        if (Math.abs(x) < 0.85) continue; // panel seams, except around the door
        box(0.012, H - 0.3, 0.01, M.brushed, x, H / 2 + 0.05, faceZ + front * 0.006, group);
      }
      box(W + 0.02, 0.1, D + 0.02, freezer ? M.blue : M.teal, 0, H - 0.12, 0, group); // colour band
      box(W + 0.01, 0.2, 0.02, M.steel, 0, 0.1, faceZ + front * 0.012, group); // kick plate
      box(1.3, 2.1, 0.03, M.black, 0, 1.05, faceZ + front * 0.015, group); // doorway
      for (let i = 0; i < 6; i++) box(0.2, 2.0, 0.01, M.pvc, -0.55 + i * 0.22, 1.05, faceZ + front * 0.035, group);
      for (const x of [-0.69, 0.69]) box(0.08, 2.2, 0.06, M.steel, x, 1.1, faceZ + front * 0.03, group);
      box(1.46, 0.08, 0.06, M.steel, 0, 2.18, faceZ + front * 0.03, group);
      const hinge = new THREE.Group();
      hinge.position.set(-0.65, 0, faceZ + front * 0.1);
      group.add(hinge);
      rbox(1.3, 2.08, 0.1, 0.03, M.steel, 0.65, 1.05, 0, hinge);
      box(0.05, 0.55, 0.05, M.black, 1.15, 1.1, front * 0.08, hinge); // handle
      box(0.14, 0.18, 0.06, M.darkSteel, 1.15, 1.42, front * 0.06, hinge); // latch
      for (const y of [0.4, 1.7]) box(0.1, 0.18, 0.08, M.darkSteel, 0.03, y, 0, hinge); // hinges
      box(0.56, 0.34, 0.04, M.black, 1.05, 1.62, faceZ + front * 0.02, group);
      const display = screen(0.48, 0.26, group, 1.05, 1.62, faceZ + front * 0.045, facing(front), drawReading);
      const unitZ = -front * 0.6;
      rbox(1.3, 0.42, 0.9, 0.04, M.brushed, 0.45, H + 0.21, unitZ, group); // condensing unit
      cyl(0.3, 0.3, 0.03, M.black, 0.45, H + 0.43, unitZ, group, 32); // fan
      box(0.62, 0.015, 0.04, M.darkSteel, 0.45, H + 0.45, unitZ, group);
      box(0.04, 0.015, 0.62, M.darkSteel, 0.45, H + 0.45, unitZ, group);
      contactShadow(W + 0.7, D + 0.7, group);
      return { height: 3.1, glow: [body], hinge, openAngle: -front * 1.9, front, display,
               top: [0.45, H + 0.5, unitZ], doorway: [0, 1.05, faceZ + front * 0.25] };
    },

    // A combi oven on a stand under an extraction hood, with ducks roasting behind a glass door.
    oven(zone, group, front) {
      const body = std(0xc6ccd4, 0.88, 0.3);
      for (const x of [-1.05, 1.05]) for (const z of [-0.65, 0.65]) box(0.06, 0.52, 0.06, M.steel, x, 0.26, z, group);
      box(2.2, 0.03, 1.4, M.steel, 0, 0.12, 0, group);
      box(2.25, 0.05, 1.45, M.steel, 0, 0.52, 0, group);
      rbox(2.3, 1.75, 1.6, 0.06, body, 0, 1.42, 0, group);
      const faceZ = front * 0.8;
      rbox(1.55, 1.3, 0.08, 0.03, M.black, -0.25, 1.42, faceZ + front * 0.03, group); // door frame
      box(1.32, 1.06, 0.02, M.warmLight, -0.25, 1.42, faceZ + front * 0.075, group); // lit oven interior
      for (const y of [1.2, 1.66]) {
        box(1.2, 0.02, 0.02, M.steel, -0.25, y + 0.2, faceZ + front * 0.1, group); // rack rail
        for (const x of [-0.7, -0.25, 0.2]) {
          ball(0.13, M.duck, x, y, faceZ + front * 0.11, group).scale.set(0.85, 1.35, 0.6);
          box(0.01, 0.12, 0.01, M.steel, x, y + 0.14, faceZ + front * 0.11, group);
        }
      }
      box(1.36, 1.1, 0.02, M.glass, -0.25, 1.42, faceZ + front * 0.15, group); // glass
      box(0.05, 0.9, 0.06, M.steel, 0.42, 1.42, faceZ + front * 0.2, group); // handle
      box(0.5, 1.3, 0.04, M.black, 0.83, 1.42, faceZ + front * 0.03, group); // control panel
      const display = screen(0.38, 0.26, group, 0.83, 1.78, faceZ + front * 0.056, facing(front),
        (pen, w, h, value = "", alert = false) => drawPanel(pen, w, h, "ROAST", value, alert));
      cyl(0.06, 0.06, 0.05, M.steel, 0.83, 1.35, faceZ + front * 0.06, group).rotation.x = Math.PI / 2;
      const light = new THREE.PointLight(0xff8a3d, 3, 3.5);
      light.position.set(-0.25, 1.4, faceZ + front * 0.6);
      group.add(light);
      rbox(2.9, 0.4, 2.1, 0.05, M.brushed, 0, 3.0, front * 0.15, group); // extraction hood
      cyl(0.25, 0.25, 0.6, M.brushed, 0, 3.45, -front * 0.3, group);
      contactShadow(3.2, 2.4, group);
      return { height: 3.5, glow: [body], front, display,
               top: [-0.85, 2.32, front * 0.4], doorway: [-0.25, 1.4, faceZ + front * 0.3] };
    },

    // A heated holding cabinet with roast ducks on shelves behind glass doors.
    hot_cabinet(zone, group, front) {
      const body = std(0xc6ccd4, 0.88, 0.3);
      for (const x of [-1.15, 1.15]) for (const z of [-0.55, 0.55]) cyl(0.04, 0.04, 0.2, M.darkSteel, x, 0.1, z, group);
      rbox(2.6, 1.7, 1.3, 0.05, body, 0, 1.05, 0, group);
      const faceZ = front * 0.65;
      box(2.3, 1.3, 0.02, M.warmLight, 0, 1.08, faceZ + front * 0.005, group);
      for (const y of [0.7, 1.22]) {
        box(2.3, 0.03, 0.2, M.steel, 0, y, faceZ + front * 0.05, group);
        for (const x of [-0.8, -0.3, 0.2, 0.7]) ball(0.12, M.duck, x, y + 0.13, faceZ + front * 0.07, group).scale.set(1, 1.1, 0.7);
      }
      for (const x of [-0.58, 0.58]) box(1.12, 1.3, 0.02, M.glass, x, 1.08, faceZ + front * 0.14, group);
      box(0.05, 1.3, 0.04, M.steel, 0, 1.08, faceZ + front * 0.15, group);
      for (const x of [-0.1, 0.1]) box(0.03, 0.4, 0.04, M.black, x, 1.1, faceZ + front * 0.18, group);
      box(0.5, 0.3, 0.04, M.black, 0.85, 1.82, faceZ + front * 0.02, group);
      const display = screen(0.42, 0.24, group, 0.85, 1.82, faceZ + front * 0.045, facing(front), drawReading);
      const light = new THREE.PointLight(0xff9a4a, 1.6, 2.6);
      light.position.set(0, 1.1, faceZ + front * 0.5);
      group.add(light);
      contactShadow(3.0, 1.8, group);
      return { height: 2.5, glow: [body], front, display, top: [0, 1.95, 0] };
    },

    // The dim sum forming machine feeding a conveyor, with an operator touchscreen and signal tower.
    forming(zone, group, front) {
      const machineX = -zone.w / 2 + 1.1;
      const body = std(0xc6ccd4, 0.88, 0.3);
      rbox(1.6, 0.18, 1.5, 0.04, M.darkSteel, machineX, 0.09, 0, group); // plinth
      rbox(1.5, 1.35, 1.4, 0.06, body, machineX, 0.86, 0, group);
      rbox(1.1, 0.35, 0.9, 0.04, M.brushed, machineX, 1.71, 0, group); // forming head
      rbox(1.25, 0.5, 1.05, 0.05, M.glass, machineX, 1.78, 0, group); // clear guard
      cyl(0.5, 0.18, 0.65, M.steel, machineX, 2.26, -front * 0.15, group, 32); // filling hopper
      cyl(0.47, 0.47, 0.02, M.filling, machineX, 2.56, -front * 0.15, group, 32);
      cyl(0.18, 0.18, 1.0, M.dough, machineX + 0.55, 1.98, 0, group).rotation.x = Math.PI / 2; // dough sheet roll
      cyl(0.03, 0.03, 0.6, M.darkSteel, machineX + 0.5, 1.8, front * 0.85, group); // touchscreen arm
      rbox(0.58, 0.4, 0.05, 0.02, M.black, machineX + 0.5, 2.18, front * 0.9, group);
      const display = screen(0.5, 0.32, group, machineX + 0.5, 2.18, front * 0.93, facing(front),
        (pen, w, h, value = "", alert = false) => drawPanel(pen, w, h, alert ? "LINE STOPPED" : "FORMING", value, alert));
      cyl(0.08, 0.08, 0.04, M.yellow, machineX - 0.45, 1.2, front * 0.71, group).rotation.x = Math.PI / 2; // e-stop
      cyl(0.055, 0.065, 0.07, M.red, machineX - 0.45, 1.2, front * 0.75, group).rotation.x = Math.PI / 2;
      const andon = andonTower(group, machineX - 0.55, 1.53, -front * 0.5);
      const start = machineX + 0.75, end = zone.w / 2 - 0.95;
      conveyor(group, (start + end) / 2, end - start);
      // A trolley of steamer baskets at the end of the line.
      const trolleyX = zone.w / 2 - 0.45;
      box(0.62, 0.03, 0.62, M.steel, trolleyX, 0.75, 0, group);
      box(0.62, 0.03, 0.62, M.steel, trolleyX, 0.25, 0, group);
      for (const x of [-0.29, 0.29]) for (const z of [-0.29, 0.29]) {
        box(0.03, 0.75, 0.03, M.steel, trolleyX + x, 0.4, z, group);
        cyl(0.04, 0.04, 0.03, M.rubber, trolleyX + x, 0.04, z, group).rotation.x = Math.PI / 2;
      }
      const baskets = [...Array(4)].map((_, i) => cyl(0.26, 0.26, 0.13, M.basket, trolleyX, 0.84 + i * 0.14, 0, group, 28));
      const lid = cyl(0.27, 0.27, 0.04, M.basketLid, trolleyX, 1.39, 0, group, 28);
      // Dim sum riding the belt.
      const pieces = [...Array(8)].map(() => {
        const piece = new THREE.Group();
        ball(0.13, M.dough, 0, 0, 0, piece).scale.set(1, 0.7, 0.85);
        add(new THREE.ConeGeometry(0.06, 0.1, 10), M.dough, 0, 0.09, 0, piece);
        piece.position.y = 1.06;
        group.add(piece);
        return piece;
      });
      contactShadow(zone.w - 0.3, 2.0, group);
      return { height: 2.9, glow: [body], pieces, pieceStart: start + 0.15, pieceSpan: end - start - 0.3, baskets, lid,
               top: [machineX - 0.55, 2.33, -front * 0.5], andon, front, display };
    },

    // The AI quality check: an inspection tunnel over the line, a camera monitor and a reject bin.
    quality(zone, group, front) {
      const body = std(0xd6dbe1, 0.7, 0.35);
      conveyor(group, 0, zone.w - 0.4);
      for (const x of [-0.75, 0.35]) for (const z of [-0.47, 0.47]) box(0.06, 0.95, 0.06, M.aluminium, x, 0.48, z, group);
      rbox(1.25, 0.72, 1.05, 0.06, body, -0.2, 1.38, 0, group); // inspection tunnel
      box(1.05, 0.03, 0.85, M.ledWhite, -0.2, 1.01, 0, group); // ring light underneath
      cyl(0.14, 0.16, 0.2, M.black, -0.2, 1.84, 0, group); // camera
      ball(0.06, M.glass, -0.2, 1.96, 0, group);
      const beam = new THREE.MeshBasicMaterial({ color: 0x17b26a, toneMapped: false });
      box(0.03, 0.01, 0.62, beam, -0.2, 0.985, 0, group); // scan line across the belt
      // Camera feed monitor on a pole beside the line.
      cyl(0.03, 0.03, 1.5, M.darkSteel, 0.85, 0.75, front * 0.6, group);
      rbox(0.68, 0.46, 0.05, 0.02, M.black, 0.85, 1.6, front * 0.62, group);
      const display = screen(0.6, 0.38, group, 0.85, 1.6, front * 0.65, facing(front), drawCameraFeed);
      const andon = andonTower(group, 0.25, 1.74, -front * 0.35);
      // Pneumatic pusher and a red reject bin on the far side of the belt.
      cyl(0.05, 0.05, 0.4, M.aluminium, 1.15, 1.05, front * 0.5, group).rotation.x = Math.PI / 2;
      const binX = 1.2, binZ = -front * 0.95;
      box(0.8, 0.06, 0.7, M.red, binX, 0.03, binZ, group);
      for (const [w, d, x, z] of [[0.8, 0.06, 0, -0.32], [0.8, 0.06, 0, 0.32], [0.06, 0.7, -0.37, 0], [0.06, 0.7, 0.37, 0]]) {
        box(w, 0.5, d, M.red, binX + x, 0.28, binZ + z, group);
      }
      const rejects = [...Array(3)].map(() => box(0.36, 0.07, 0.26, M.dough, binX, 1.0, 0.3, group));
      rejects.forEach((tray) => (tray.visible = false));
      const trays = [...Array(3)].map(() => {
        const tray = new THREE.Group();
        rbox(0.42, 0.04, 0.3, 0.015, M.steel, 0, 0, 0, tray);
        for (const [dx, dz] of [[-0.1, -0.06], [0.1, -0.06], [-0.1, 0.06], [0.1, 0.06]]) {
          ball(0.06, M.dough, dx, 0.04, dz, tray).scale.set(1, 0.7, 0.9);
        }
        tray.position.y = 1.0;
        group.add(tray);
        return tray;
      });
      contactShadow(zone.w, 2.2, group);
      return { height: 2.6, glow: [body], beam, top: [0.25, 2.55, -front * 0.35], rejects, binX, binZ, andon, front, display,
               trays, trayStart: -zone.w / 2 + 0.45, traySpan: zone.w - 0.9 };
    },

    // The cold prep area: stainless prep tables with boards and bowls of filling.
    prep(zone, group, front) {
      const top = std(0xc6ccd4, 0.88, 0.3);
      for (const z of [-0.7, 0.7]) {
        rbox(3.4, 0.05, 0.78, 0.02, top, 0, 0.9, z, group);
        box(3.3, 0.03, 0.7, M.steel, 0, 0.3, z, group);
        for (const x of [-1.6, 1.6]) for (const dz of [-0.33, 0.33]) cyl(0.025, 0.025, 0.88, M.steel, x, 0.45, z + dz, group, 12);
        rbox(0.5, 0.025, 0.34, 0.01, M.board, -0.9, 0.94, z, group);
        rbox(0.5, 0.025, 0.34, 0.01, M.board, 0.6, 0.94, z, group);
        [[0xf2a7a0, -0.25], [0x6bab5a, 0.1], [0x8b5a3c, 1.2]].forEach(([color, x]) => {
          cyl(0.15, 0.1, 0.1, M.steel, x, 0.98, z, group, 20);
          cyl(0.13, 0.13, 0.02, std(color, 0, 0.7), x, 1.025, z, group, 20);
        });
      }
      contactShadow(zone.w - 0.2, zone.d - 0.6, group);
      return { height: 1.5, glow: [top], front, top: [0, 1.1, 0] };
    },

    // Goods in (pallets of cartons and a pallet jack) or goods out (rack trolleys and insulated boxes).
    dock(zone, group, front) {
      const dispatch = zone.name === "Dispatch";
      if (dispatch) {
        for (const x of [-0.75, 0]) { // speed-rack trolleys of trays
          for (const dx of [-0.25, 0.25]) for (const dz of [-0.3, 0.3]) box(0.03, 1.7, 0.03, M.steel, x + dx, 0.88, dz, group);
          for (let i = 0; i < 7; i++) box(0.5, 0.02, 0.62, i % 2 ? M.white : M.dough, x, 0.3 + i * 0.22, 0, group);
          for (const dx of [-0.25, 0.25]) for (const dz of [-0.3, 0.3]) cyl(0.04, 0.04, 0.03, M.rubber, x + dx, 0.04, dz, group).rotation.x = Math.PI / 2;
        }
        pallet(group, 0.9, 0.2);
        for (const [y, dz] of [[0.15, -0.22], [0.15, 0.22], [0.55, -0.22]]) rbox(0.7, 0.4, 0.42, 0.03, M.insulated, 0.9, y + 0.2, 0.2 + dz, group);
      } else {
        for (const [x, z] of [[-0.6, -0.5], [0.6, 0.5]]) {
          pallet(group, x, z);
          for (const layer of [0, 1]) for (const dx of [-0.24, 0.24]) for (const dz of [-0.24, 0.24]) {
            carton(group, 0.46, 0.36, 0.46, x + dx, 0.155 + layer * 0.37, z + dz);
          }
        }
        // A yellow pallet jack.
        box(0.18, 0.06, 1.0, M.yellow, 0.55, 0.05, -0.6, group);
        box(0.18, 0.06, 1.0, M.yellow, 0.9, 0.05, -0.6, group);
        rbox(0.5, 0.25, 0.25, 0.03, M.yellow, 0.72, 0.18, -1.15, group);
        const handle = box(0.04, 0.9, 0.04, M.black, 0.72, 0.65, -1.3, group);
        handle.rotation.x = -0.35;
      }
      // Extra stock stacked up for a large banquet order.
      const extra = new THREE.Group();
      group.add(extra);
      pallet(extra, dispatch ? -0.4 : -0.6, dispatch ? 1.1 : 0.6).position.y = 0;
      for (const layer of [0, 1, 2]) for (const dx of [-0.24, 0.24]) {
        carton(extra, 0.46, 0.36, 0.9, (dispatch ? -0.4 : -0.6) + dx, 0.155 + layer * 0.37, dispatch ? 1.1 : 0.6, dispatch ? M.insulated : M.cardboard);
      }
      contactShadow(zone.w - 0.3, zone.d - 0.3, group);
      return { height: 2.2, glow: [], extra, front, top: [0, 1.8, 0] };
    },

    // A restaurant table with a cloth, chairs, seated guests and steamer baskets.
    table(zone, group) {
      cyl(0.74, 0.74, 0.05, M.cloth, 0, 0.77, 0, group, 40);
      add(new THREE.CylinderGeometry(0.74, 0.76, 0.3, 40, 1, true), M.cloth, 0, 0.6, 0, group);
      cyl(0.08, 0.25, 0.45, M.darkSteel, 0, 0.23, 0, group);
      const coats = [0x5b7fa6, 0xa65b5b, 0x6b8f71, 0xb08a4f];
      for (let i = 0; i < 4; i++) {
        // Chairs sit on the diagonals, leaving the sides free for the robot.
        const seat = new THREE.Group();
        seat.rotation.y = Math.PI / 4 + (i * Math.PI) / 2;
        group.add(seat);
        rbox(0.44, 0.07, 0.44, 0.03, M.chair, 1.0, 0.46, 0, seat);
        rbox(0.07, 0.55, 0.42, 0.03, M.chair, 1.2, 0.74, 0, seat);
        for (const [dx, dz] of [[-0.18, -0.18], [-0.18, 0.18], [0.18, -0.18], [0.18, 0.18]]) cyl(0.02, 0.02, 0.44, M.chair, 1.0 + dx, 0.22, dz, seat, 8);
        if (i < zone.guests) guest(seat, coats[i]).position.x = 1.0;
      }
      const dishes = new THREE.Group(); // steamer baskets, shown once the table has its food
      group.add(dishes);
      for (const [x, z] of [[-0.25, -0.1], [0.22, -0.2], [0.05, 0.28]]) {
        cyl(0.17, 0.17, 0.1, M.basket, x, 0.85, z, dishes, 24);
        cyl(0.175, 0.175, 0.03, M.basketLid, x, 0.91, z, dishes, 24);
      }
      for (const a of [0.4, 2.0, 3.6, 5.2]) cyl(0.11, 0.11, 0.01, M.white, Math.cos(a) * 0.52, 0.8, Math.sin(a) * 0.52, group, 20);
      contactShadow(2.6, 2.6, group);
      return { height: 1.2, glow: [], dishes };
    },

    // The kitchen pass: a stainless counter under heat lamps, where dishes wait for the robot.
    pass(zone, group) {
      const counter = std(0xc6ccd4, 0.88, 0.3);
      rbox(1.0, 1.0, zone.d - 0.4, 0.04, counter, 0, 0.5, 0, group);
      for (const z of [-(zone.d - 0.9) / 2, (zone.d - 0.9) / 2]) box(0.06, 0.8, 0.06, M.steel, 0, 1.4, z, group);
      rbox(0.4, 0.1, zone.d - 0.7, 0.03, M.brushed, 0, 1.82, 0, group); // heat-lamp gantry
      for (let i = 0; i < 4; i++) cyl(0.07, 0.1, 0.08, M.warmLight, 0, 1.74, -1.2 + i * 0.8, group, 16);
      for (const z of [-0.9, 0, 0.9]) {
        cyl(0.2, 0.2, 0.13, M.basket, 0, 1.07, z, group, 24);
        cyl(0.205, 0.205, 0.03, M.basketLid, 0, 1.15, z, group, 24);
      }
      const extra = new THREE.Group(); // dishes piling up during a lunch rush
      group.add(extra);
      for (const z of [-1.3, -0.45, 0.45, 1.3]) for (const level of [0, 1]) {
        cyl(0.2, 0.2, 0.13, M.basket, 0.15, 1.07 + 0.15 * level, z, extra, 24);
      }
      contactShadow(1.6, zone.d, group);
      return { height: 2.1, glow: [counter], extra };
    },
  };

  // ---- Robots -----------------------------------------------------------------------------
  // Each model is built into `body` (which turns to face its direction of travel; +x is forward).
  // `lamp` is the status light material. Returns what it carries, its label height, and a part to spin.
  const robots = {
    amr(body, lamp) { // low autonomous tray carrier with a lidar on top
      rbox(1.05, 0.26, 0.74, 0.07, std(0xe4e7ec, 0.2, 0.45), 0, 0.22, 0, body);
      box(1.07, 0.06, 0.76, M.black, 0, 0.12, 0, body); // bumper
      for (const x of [-0.35, 0.35]) for (const z of [-0.37, 0.37]) cyl(0.08, 0.08, 0.06, M.rubber, x, 0.08, z, body).rotation.x = Math.PI / 2;
      box(0.02, 0.05, 0.5, lamp, 0.53, 0.25, 0, body); // status light strip
      box(0.8, 0.03, 0.6, M.darkSteel, -0.08, 0.37, 0, body); // deck
      const spin = new THREE.Group();
      spin.position.set(0.35, 0.37, 0);
      body.add(spin);
      cyl(0.09, 0.1, 0.09, M.black, 0, 0.045, 0, spin, 20);
      box(0.06, 0.03, 0.02, M.ledWhite, 0.07, 0.06, 0, spin); // lidar window
      const cargo = new THREE.Group();
      body.add(cargo);
      for (const y of [0.5, 0.74]) rbox(0.6, 0.22, 0.44, 0.03, M.blueCrate, -0.1, y, 0, cargo);
      contactShadow(1.3, 1.0, body);
      return { cargo, labelY: 2.1, spin };
    },
    server(body, lamp) { // tall three-tray serving robot with a face screen
      cyl(0.34, 0.38, 0.28, M.black, 0, 0.14, 0, body, 28);
      rbox(0.12, 1.3, 0.5, 0.04, M.white, -0.26, 0.92, 0, body); // spine
      for (const y of [0.5, 0.88, 1.26]) cyl(0.33, 0.33, 0.04, M.white, 0, y, 0, body, 28);
      rbox(0.14, 0.32, 0.52, 0.05, M.black, -0.2, 1.7, 0, body); // head
      for (const z of [-0.11, 0.11]) ball(0.045, lamp, -0.125, 1.72, z, body);
      const cargo = new THREE.Group();
      body.add(cargo);
      for (const y of [1.35, 0.97]) {
        cyl(0.2, 0.2, 0.12, M.basket, 0.05, y, 0, cargo, 24);
        cyl(0.205, 0.205, 0.03, M.basketLid, 0.05, y + 0.07, 0, cargo, 24);
      }
      contactShadow(0.9, 0.9, body);
      return { cargo, labelY: 2.5, spin: null };
    },
  };

  // ---- Floors ---------------------------------------------------------------------------------
  // Tile or plank textures drawn on a canvas, repeated across the floor.
  function floorTexture(kind) {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 512;
    const pen = canvas.getContext("2d");
    if (kind === "wood") {
      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 2; col++) {
          const tone = 196 + Math.floor(Math.random() * 22);
          pen.fillStyle = `rgb(${tone + 22},${tone}, ${tone - 42})`;
          const offset = row % 2 ? 128 : 0;
          pen.fillRect(col * 256 - offset, row * 64, 256, 64);
          pen.fillRect(col * 256 - offset + 512, row * 64, 256, 64);
        }
        pen.fillStyle = "rgba(90,60,30,0.25)";
        pen.fillRect(0, row * 64, 512, 2);
      }
    } else {
      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
          const tone = 216 + Math.floor(Math.random() * 8);
          pen.fillStyle = `rgb(${tone},${tone + 3},${tone + 7})`;
          pen.fillRect(col * 64, row * 64, 64, 64);
        }
      }
      pen.fillStyle = "#c2c8d0";
      for (let i = 0; i <= 8; i++) {
        pen.fillRect(i * 64 - 1, 0, 2, 512);
        pen.fillRect(0, i * 64 - 1, 512, 2);
      }
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.anisotropy = 8;
    return texture;
  }

  return { M, std, add, box, rbox, cyl, ball, contactShadow, builders, robots, person, floorTexture };
}
