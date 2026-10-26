// 3D digital twins (the kitchen, and the restaurant dining room), drawn with three.js.
//
// Python (twin/__init__.py) sends the full state on every refresh: the zones
// with their label and alert flag, and the robot position. This file only
// draws that state. It builds the scene once, then updates it in place so the
// camera stays where the viewer left it.
//
// Clicking a zone (or the robot) selects it: the camera glides over and an
// inspector panel shows its reading with buttons that send Python a trigger:
// "scenario" (switch its demo fault on or off) or "clicked" (open its page).

const VENDOR = new URL("app/static/vendor/", document.baseURI).href;

const COLOR = {
  floor: 0xe6e9ed, pad: 0xe9edf1, wall: 0xf1f3f6,
  cold: 0xd8e5f1, steel: 0xc5cbd3, dark: 0x343a46, belt: 0x4b5260,
  crate: 0xc9a66b, dough: 0xfdf6e3, warm: 0xeb6834, accent: 0xb42318,
  alert: 0xd03b3b, ok: 0x0ca30c,
  cloth: 0xfbf7ee, wood: 0x8a5a36, basket: 0xd9b77e, roast: 0x8a4b1f, white: 0xf3f3f1,
};
const SHIRTS = [0x5b7fa6, 0xa65b5b, 0x6b8f71, 0xb08a4f]; // guests' clothes
const SELECTED = 0x2a78d6; // floor tint of the selected zone

// Material Symbols icon for each kind of zone, shown in the inspector panel.
const ICONS = {
  cold_room: "kitchen", oven: "oven_gen", hot_cabinet: "local_fire_department", forming: "conveyor_belt",
  quality: "document_scanner", prep: "countertops", dock: "local_shipping", table: "table_restaurant",
  pass: "room_service", amr: "robot_2", server: "room_service",
};

const escapeHtml = (text) =>
  String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Starting camera for each page: where it stands, what it looks at, and how big labels are.
// Close-ups hide the robot's label, which would fill the view when it drives past.
// fitWidth: the camera backs off until this many metres fit across the view, so the
// whole floor shows at any card width (until the viewer moves the camera themselves).
const CAMERAS = {
  overview: { from: [0, 12, 14], to: [0, 0, 0.2], labelSize: 3.6, fitWidth: 36 },
  cold_rooms: { from: [0, 9, 8.5], to: [0, 1.2, -4.5], labelSize: 3.0 },
  amr: { from: [0, 26, 13], to: [0, 0, -0.8], labelSize: 3.3 },
  forming: { from: [-0.9, 4.4, 12.4], to: [-0.9, 1.3, 5.5], labelSize: 2.2, hideRobotLabel: true },
  oven: { from: [5.9, 5.0, 1.6], to: [5.9, 2.0, -5.5], labelSize: 2.2, hideRobotLabel: true },
  dining: { from: [0, 9.5, 9.0], to: [0, 0, 0.3], labelSize: 1.7, fitWidth: 17 },
};

const twins = new WeakMap(); // one scene per mounted component

export default async function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!twins.has(parentElement)) twins.set(parentElement, build(parentElement, data));
  (await twins.get(parentElement)).update(data, setTriggerValue);
}

async function build(parent, data) {
  const THREE = await import(VENDOR + "three.module.min.js");
  const { OrbitControls } = await import(VENDOR + "OrbitControls.js");
  const { RoundedBoxGeometry } = await import(VENDOR + "RoundedBoxGeometry.js");
  const { RoomEnvironment } = await import(VENDOR + "RoomEnvironment.js");
  const kit = createModels(THREE, RoundedBoxGeometry); // twin/models.js
  const dining = data.focus === "dining";

  // ---- Renderer, camera, lights -------------------------------------------
  const box = document.createElement("div");
  box.className = "twin-box";
  const boxHeight = data.fill ? `calc(100vh - ${data.fill}px)` : `${data.height}px`;
  box.style.cssText = `width:100%;height:${boxHeight};border-radius:12px;overflow:hidden;` +
    "background:radial-gradient(120% 90% at 50% 0%, #ffffff 0%, #eef1f5 60%, #e6eaf0 100%);";
  parent.appendChild(box);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); // transparent: the box's gradient shows through
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; // filmic contrast, so lit metal and glass look real
  renderer.toneMappingExposure = 1.05;
  box.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  // A soft studio "room" reflected in every surface: this is what makes stainless steel read as metal.
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;

  const view = CAMERAS[data.focus] || CAMERAS.overview;
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  camera.position.set(...view.from);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(...view.to);
  controls.enableDamping = true;
  let viewerMoved = false;
  let lastActivity = performance.now(); // last time the viewer did anything with the 3D view
  controls.addEventListener("start", () => {
    viewerMoved = true;
    lastActivity = performance.now();
    // The viewer took over the camera: stop any glide. A fly-in still in the air lands at once.
    if (glide?.intro) {
      camera.position.copy(glide.toPos);
      controls.target.copy(glide.toTarget);
    }
    glide = null;
  });
  controls.maxPolarAngle = Math.PI * 0.47; // never look from below the floor
  controls.minDistance = 6;
  controls.maxDistance = 60;

  scene.add(new THREE.HemisphereLight(0xffffff, 0xcfd6df, 0.7));
  const sun = new THREE.DirectionalLight(0xfff8f0, 2.4); // key light, casting the shadows
  sun.position.set(8, 20, 12);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.03;
  Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 18, bottom: -18 });
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xdfe8ff, 0.6); // cool fill from the other side
  fill.position.set(-10, 8, -6);
  scene.add(fill);

  // ---- Small helpers --------------------------------------------------------
  const material = (color, extra = {}) =>
    new THREE.MeshStandardMaterial({ color, roughness: 0.75, metalness: 0.05, ...extra });

  function addMesh(geometry, mat, x, y, z, group) {
    const mesh = new THREE.Mesh(geometry, mat);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  }
  const addBox = (w, h, d, mat, x, y, z, group) => addMesh(new THREE.BoxGeometry(w, h, d), mat, x, y, z, group);

  // A floating name tag. setText() redraws it only when the text changes.
  const redrawLabels = []; // called once the app font (Inter) has loaded
  const labelSprites = []; // every name tag, for the fade-in after the opening fly-in
  function makeLabel(y, group) {
    const canvas = document.createElement("canvas");
    canvas.width = 380;
    canvas.height = 124;
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false, toneMapped: false }));
    sprite.scale.set(view.labelSize, view.labelSize * canvas.height / canvas.width, 1);
    sprite.position.y = y;
    sprite.renderOrder = 10;
    labelSprites.push(sprite);
    group.add(sprite);

    let shown = "";
    let last = ["", "", false];
    function draw(title, detail, alert) {
      const pen = canvas.getContext("2d");
      const font = "Inter, system-ui, sans-serif";
      pen.clearRect(0, 0, canvas.width, canvas.height);
      // A white rounded card with a soft shadow; red outline when the zone is in alert.
      pen.save();
      pen.shadowColor = "rgba(16, 24, 40, 0.18)";
      pen.shadowBlur = 14;
      pen.shadowOffsetY = 4;
      pen.fillStyle = "#ffffff";
      pen.beginPath();
      pen.roundRect(10, 8, canvas.width - 20, canvas.height - 22, 26);
      pen.fill();
      pen.restore();
      if (alert) {
        pen.strokeStyle = "#d92d20";
        pen.lineWidth = 6;
        pen.beginPath();
        pen.roundRect(10, 8, canvas.width - 20, canvas.height - 22, 26);
        pen.stroke();
      }
      pen.textAlign = "center";
      pen.fillStyle = "#101828";
      pen.font = `650 44px ${font}`;
      pen.fillText(title, canvas.width / 2, detail ? 50 : 68, canvas.width - 44);
      if (detail) {
        pen.fillStyle = alert ? "#b42318" : "#475467";
        pen.font = `550 37px ${font}`;
        pen.fillText((alert ? "⚠ " : "") + detail, canvas.width / 2, 91, canvas.width - 44);
      }
      texture.needsUpdate = true;
    }
    redrawLabels.push(() => draw(...last));
    return function setText(title, detail, alert) {
      const text = `${title}|${detail}|${alert}`;
      if (text === shown) return;
      shown = text;
      last = [title, detail, alert];
      draw(title, detail, alert);
    };
  }
  document.fonts.load("650 40px Inter").then(() => redrawLabels.forEach((redraw) => redraw()));

  // ---- Floor and walls ------------------------------------------------------
  const { width: floorW, depth: floorD } = data.floor;
  const floorMap = kit.floorTexture(dining ? "wood" : "tile");
  floorMap.repeat.set(floorW / 4.8, floorD / 4.8); // 0.6 m tiles, or planks in the dining room
  const floor = addBox(floorW, 0.2, floorD, kit.std(0xffffff, 0, 0.5, { map: floorMap }), 0, -0.1, 0, scene);
  floor.castShadow = false;
  const wallMap = kit.floorTexture("tile");
  wallMap.repeat.set(floorW / 2.4, 3 / 2.4);
  const wall = dining ? kit.std(0xefe6da, 0, 0.8) : kit.std(0xf6f7f9, 0, 0.45, { map: wallMap });
  addBox(floorW, 3, 0.2, wall, 0, 1.5, -floorD / 2, scene);
  addBox(0.2, 3, floorD, wall, -floorW / 2, 1.5, 0, scene);
  addBox(0.2, 3, floorD, wall, floorW / 2, 1.5, 0, scene);
  const skirting = kit.std(dining ? 0x7a4f2e : 0x98a2b3, 0.3, 0.5);
  addBox(floorW, 0.15, 0.24, skirting, 0, 0.075, -floorD / 2, scene);
  for (const x of [-floorW / 2, floorW / 2]) addBox(0.24, 0.15, floorD, skirting, x, 0.075, 0, scene);
  if (!dining) {
    // Yellow lines marking the aisle between the two rows of equipment.
    for (const z of [-3.2, 3.2]) addBox(floorW - 0.4, 0.01, 0.1, kit.M.yellow, 0, 0.005, z, scene).castShadow = false;
    // A fire extinguisher and a lit exit sign on the walls.
    kit.cyl(0.11, 0.11, 0.5, kit.M.red, -floorW / 2 + 0.25, 0.75, 1.6, scene);
    kit.box(0.16, 0.2, 0.12, kit.M.black, -floorW / 2 + 0.25, 1.08, 1.6, scene);
    addBox(0.05, 0.3, 0.9, new THREE.MeshBasicMaterial({ color: 0x12b76a, toneMapped: false }), -floorW / 2 + 0.13, 2.6, 0, scene);
  }

  scene.add(Object.assign(new THREE.Group(), { name: "safety-zones" }));
  for (const zone of data.safety_zones) {
    const safetyZones = scene.getObjectByName("safety-zones");
    const overlay = addBox(zone.w, 0.02, zone.d,
      material(zone.color, { transparent: true, opacity: 0.38, depthWrite: false }),
      zone.x, 0.07, zone.z, safetyZones);
    overlay.castShadow = false;
    const outline = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(zone.w, 0.02, zone.d)),
      new THREE.LineBasicMaterial({ color: zone.color }),
    );
    outline.position.set(zone.x, 0.07, zone.z);
    safetyZones.add(outline);
  }

  const zones = {};
  const clickable = []; // groups the viewer can click to select
  for (const zone of data.zones) {
    const group = new THREE.Group();
    group.position.set(zone.x, 0, zone.z);
    group.userData.name = zone.name;
    clickable.push(group);
    scene.add(group);
    const pad = material(COLOR.pad);
    addBox(zone.w - 0.15, 0.06, zone.d - 0.15, pad, 0, 0.03, 0, group).castShadow = false;
    if (!dining) { // yellow floor markings around each work cell
      for (const z of [-(zone.d - 0.15) / 2, (zone.d - 0.15) / 2]) addBox(zone.w - 0.15, 0.065, 0.06, kit.M.yellow, 0, 0.033, z, group).castShadow = false;
      for (const x of [-(zone.w - 0.15) / 2, (zone.w - 0.15) / 2]) addBox(0.06, 0.065, zone.d - 0.15, kit.M.yellow, x, 0.033, 0, group).castShadow = false;
    }
    const parts = kit.builders[zone.kind](zone, group, zone.z < 0 ? 1 : -1);
    zones[zone.name] = { ...parts, kind: zone.kind, group, pad, setText: makeLabel(parts.height + 0.5, group),
                         baseColor: parts.glow[0]?.color.clone(), heat: null, effects: new Set(),
                         alert: false, busy: false, doorOpen: false, travelled: 0 };
  }

  // ---- The robot and its route ----------------------------------------------
  if (data.route.length) {
    const routePoints = [...data.route, data.route[0]].map(([x, z]) => new THREE.Vector3(x, 0.03, z));
    const routeLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(routePoints),
      new THREE.LineDashedMaterial({ color: COLOR.accent, dashSize: 0.35, gapSize: 0.25 }),
    );
    routeLine.computeLineDistances();
    scene.add(routeLine);
  }

  const robot = new THREE.Group();
  robot.position.set(data.amr.x, 0, data.amr.z);
  robot.userData.name = data.amr.name;
  clickable.push(robot);
  scene.add(robot);
  const robotBody = new THREE.Group(); // turns to face the direction of travel (+x is forward)
  robot.add(robotBody);
  const lamp = new THREE.MeshBasicMaterial({ color: COLOR.ok, toneMapped: false });

  const { cargo, labelY, spin } = kit.robots[data.amr.kind](robotBody, lamp);
  const obstacle = addMesh(new THREE.ConeGeometry(0.25, 0.7, 16), material(COLOR.warm), 1.1, 0.35, 0, robotBody);
  const setRobotText = view.hideRobotLabel ? () => {} : makeLabel(labelY, robot);
  const robotTarget = robot.position.clone();
  let robotBlocked = false;
  // A crate fallen in the aisle in front of a blocked robot.
  const fallenCrate = addBox(0.6, 0.45, 0.5, material(COLOR.crate), 1.25, 0.2, 0.1, robotBody);
  fallenCrate.rotation.set(0.35, 0.6, 0.25);
  fallenCrate.visible = false;

  // ---- Kitchen staff ---------------------------------------------------------
  // People at their stations sway a little; one walks up and down the aisle.
  const staff = [];
  if (!dining) {
    const stations = [[-1.7, 3.9, Math.PI], [-6.6, 4.1, Math.PI], [5.6, 3.9, Math.PI], [6.8, -3.9, 0], [-9.6, 3.6, Math.PI * 0.8]];
    for (const [x, z, turn] of stations) {
      const worker = kit.person(scene, x, z, turn);
      const phase = Math.random() * 6;
      staff.push({ animate: (time) => { worker.group.rotation.y = turn + 0.15 * Math.sin(time * 0.6 + phase); } });
    }
    const walker = kit.person(scene, -7, 1.2, Math.PI / 2);
    staff.push({
      animate(time) {
        // Walk between x = -7 and x = 2 along the aisle, turning at each end.
        const lap = (time * 0.12) % 2, going = lap < 1, along = going ? lap : 2 - lap;
        walker.group.position.x = -7 + 9 * (0.5 - 0.5 * Math.cos(Math.PI * along));
        walker.group.rotation.y = going ? Math.PI / 2 : -Math.PI / 2;
        const stride = Math.sin(time * 7) * 0.35;
        walker.legs[0].rotation.x = stride;
        walker.legs[1].rotation.x = -stride;
        walker.arms[0].rotation.x = -stride;
        walker.arms[1].rotation.x = stride;
      },
    });
  }

  // ---- Fault effects --------------------------------------------------------
  // Which effects each demo fault switches on for its zone (keys of events.EVENTS).
  const EFFECTS = {
    chiller_door_open: ["mist"],
    freezer_fault: ["smoke", "beacon"],
    forming_jam: ["smoke", "beacon"],
    oven_door_leak: ["heat", "beacon"],
    defect_spike: ["rejects", "beacon"],
    banquet_order: ["extra"],
    lunch_rush: ["extra"],
  };

  // A soft round dot for particles.
  const dotCanvas = document.createElement("canvas");
  dotCanvas.width = dotCanvas.height = 64;
  const dotPen = dotCanvas.getContext("2d");
  const glowDot = dotPen.createRadialGradient(32, 32, 0, 32, 32, 32);
  glowDot.addColorStop(0, "rgba(255,255,255,1)");
  glowDot.addColorStop(1, "rgba(255,255,255,0)");
  dotPen.fillStyle = glowDot;
  dotPen.fillRect(0, 0, 64, 64);
  const dotTexture = new THREE.CanvasTexture(dotCanvas);

  // A small particle system. `spawn(p)` places a particle (position p.at, velocity p.v, life p.ttl).
  function makeEmitter(group, { count, color, size, opacity, additive, spawn }) {
    const particles = [...Array(count)].map(() => ({ at: new THREE.Vector3(), v: new THREE.Vector3(), age: 0, ttl: 1 }));
    const positions = new Float32Array(count * 3);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const points = new THREE.Points(geometry, new THREE.PointsMaterial({
      color, size, map: dotTexture, transparent: true, opacity, depthWrite: false,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    }));
    points.visible = false;
    group.add(points);
    particles.forEach((p) => { spawn(p); p.age = Math.random() * p.ttl; }); // start staggered
    return {
      set on(value) { points.visible = value; },
      step(dt) {
        if (!points.visible) return;
        particles.forEach((p, i) => {
          p.age += dt;
          if (p.age > p.ttl) { spawn(p); p.age = 0; }
          p.at.addScaledVector(p.v, dt);
          positions.set([p.at.x, p.at.y, p.at.z], i * 3);
        });
        geometry.attributes.position.needsUpdate = true;
      },
    };
  }
  const jitter = (size) => (Math.random() - 0.5) * size;

  // A red warning beacon: a glowing bulb with a light beam sweeping round.
  function makeBeacon(group, [x, y, z]) {
    const beacon = new THREE.Group();
    beacon.position.set(x, y, z);
    beacon.visible = false;
    group.add(beacon);
    addMesh(new THREE.CylinderGeometry(0.13, 0.15, 0.08, 16), material(COLOR.dark), 0, 0.04, 0, beacon);
    addMesh(new THREE.SphereGeometry(0.13, 16, 12), new THREE.MeshBasicMaterial({ color: 0xff3b30, toneMapped: false }), 0, 0.16, 0, beacon);
    const sweep = new THREE.Mesh(
      new THREE.ConeGeometry(0.5, 1.6, 24, 1, true),
      new THREE.MeshBasicMaterial({ color: 0xff3b30, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }),
    );
    sweep.rotation.z = Math.PI / 2;
    sweep.position.x = 0.8;
    const spinner = new THREE.Group();
    spinner.position.y = 0.16;
    spinner.add(sweep);
    beacon.add(spinner);
    return { beacon, spinner };
  }

  // A pulsing map pin with "!" that floats above a zone in alert, visible from far away.
  const pinCanvas = document.createElement("canvas");
  pinCanvas.width = 128;
  pinCanvas.height = 160;
  const pinPen = pinCanvas.getContext("2d");
  pinPen.fillStyle = "#d92d20";
  pinPen.beginPath();
  pinPen.arc(64, 58, 50, Math.PI * 0.82, Math.PI * 0.18);
  pinPen.lineTo(64, 152);
  pinPen.closePath();
  pinPen.fill();
  pinPen.fillStyle = "#ffffff";
  pinPen.font = "800 68px Inter, system-ui, sans-serif";
  pinPen.textAlign = "center";
  pinPen.fillText("!", 64, 82);
  const pinTexture = new THREE.CanvasTexture(pinCanvas);
  pinTexture.colorSpace = THREE.SRGBColorSpace;
  function makePin(group, y) {
    const pin = new THREE.Sprite(new THREE.SpriteMaterial({ map: pinTexture, depthTest: false, toneMapped: false }));
    const size = view.labelSize * 0.3;
    pin.scale.set(size, size * 1.25, 1);
    pin.center.set(0.5, 0); // the pin's point sits on its position
    pin.position.y = y;
    pin.renderOrder = 11;
    pin.visible = false;
    group.add(pin);
    return { pin, y };
  }
  const labelTop = (height) => height + 0.5 + view.labelSize * 0.17 + 0.1;

  // Build the effects each zone can show (they stay hidden until its fault is on).
  for (const model of Object.values(zones)) {
    const { group, top, doorway, front } = model;
    model.pinned = makePin(group, labelTop(model.height));
    if (top) {
      model.beacon = makeBeacon(group, top);
      model.smoke = makeEmitter(group, {
        count: 55, color: 0x5d6470, size: 0.95, opacity: 0.5,
        spawn: (p) => { p.at.set(top[0] + jitter(0.4), top[1] + 0.1, top[2] + jitter(0.4)); p.v.set(jitter(0.3), 0.7 + Math.random() * 0.4, jitter(0.3)); p.ttl = 2 + Math.random(); },
      });
    }
    if (model.kind === "cold_room") {
      model.mist = makeEmitter(group, {
        count: 90, color: 0xeaf6ff, size: 1.05, opacity: 0.7,
        spawn: (p) => { p.at.set(doorway[0] + jitter(1.0), doorway[1] + jitter(1.6), doorway[2]); p.v.set(jitter(0.5), -0.25 - Math.random() * 0.2, front * (0.6 + Math.random() * 0.5)); p.ttl = 1.8 + Math.random(); },
      });
    }
    if (model.kind === "oven") {
      model.heatHaze = makeEmitter(group, {
        count: 50, color: 0xff7a1a, size: 0.45, opacity: 0.85, additive: true,
        spawn: (p) => { p.at.set(doorway[0] + jitter(1.4), doorway[1] + jitter(0.6), doorway[2]); p.v.set(jitter(0.2), 0.8 + Math.random() * 0.5, front * 0.25); p.ttl = 1 + Math.random() * 0.6; },
      });
    }
  }
  const robotPin = makePin(robot, labelY + view.labelSize * 0.17 + 0.1);

  // A green pin with a tick replaces the red "!" once a fault is fixed and readings are recovering.
  const okPinCanvas = document.createElement("canvas");
  okPinCanvas.width = 128;
  okPinCanvas.height = 160;
  const okPen = okPinCanvas.getContext("2d");
  okPen.drawImage(pinCanvas, 0, 0);
  okPen.globalCompositeOperation = "source-in";
  okPen.fillStyle = "#12b76a";
  okPen.fillRect(0, 0, 128, 160);
  okPen.globalCompositeOperation = "source-over";
  okPen.strokeStyle = "#ffffff";
  okPen.lineWidth = 12;
  okPen.lineCap = okPen.lineJoin = "round";
  okPen.beginPath();
  okPen.moveTo(40, 58);
  okPen.lineTo(57, 75);
  okPen.lineTo(88, 42);
  okPen.stroke();
  const okPinTexture = new THREE.CanvasTexture(okPinCanvas);
  okPinTexture.colorSpace = THREE.SRGBColorSpace;

  // ---- Product flow -----------------------------------------------------------
  // Chevrons move along the floor from goods in to dispatch, showing which way product travels.
  // They stop and turn red when the forming line is jammed and nothing is coming through.
  let flowStrip = null;
  if (!dining) {
    const flowCanvas = document.createElement("canvas");
    flowCanvas.width = 128;
    flowCanvas.height = 64;
    const flowPen = flowCanvas.getContext("2d");
    flowPen.fillStyle = "#ffffff";
    flowPen.beginPath();
    for (const [x, y] of [[34, 10], [70, 32], [34, 54], [52, 54], [88, 32], [52, 10]]) flowPen.lineTo(x, y);
    flowPen.closePath();
    flowPen.fill();
    const flowMap = new THREE.CanvasTexture(flowCanvas);
    flowMap.wrapS = THREE.RepeatWrapping;
    const length = 20.7; // from Receiving to Dispatch
    flowMap.repeat.set(length / 0.9, 1);
    flowStrip = new THREE.Mesh(
      new THREE.PlaneGeometry(length, 0.42),
      new THREE.MeshBasicMaterial({ map: flowMap, color: 0x17b26a, transparent: true, opacity: 0.8, depthWrite: false, toneMapped: false }),
    );
    flowStrip.rotation.x = -Math.PI / 2;
    flowStrip.position.set(-0.15, 0.02, 2.75);
    flowStrip.renderOrder = 1;
    scene.add(flowStrip);
  }

  // ---- Resolving a fault --------------------------------------------------------
  // When a fault is switched off, a technician walks over, works on the machine for a moment,
  // and a green tick bursts above it.
  const tickCanvas = document.createElement("canvas");
  tickCanvas.width = tickCanvas.height = 128;
  const tickPen = tickCanvas.getContext("2d");
  tickPen.fillStyle = "#12b76a";
  tickPen.beginPath();
  tickPen.arc(64, 64, 58, 0, Math.PI * 2);
  tickPen.fill();
  tickPen.strokeStyle = "#ffffff";
  tickPen.lineWidth = 14;
  tickPen.lineCap = tickPen.lineJoin = "round";
  tickPen.beginPath();
  tickPen.moveTo(36, 66);
  tickPen.lineTo(56, 86);
  tickPen.lineTo(94, 44);
  tickPen.stroke();
  const tickTexture = new THREE.CanvasTexture(tickCanvas);
  tickTexture.colorSpace = THREE.SRGBColorSpace;

  const bursts = []; // tick bursts currently playing
  function burstAt(position, height) {
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tickTexture, depthTest: false, transparent: true, toneMapped: false }));
    sprite.position.copy(position).setY(height);
    sprite.renderOrder = 12;
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.85, 1, 48),
      new THREE.MeshBasicMaterial({ color: 0x12b76a, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.copy(position).setY(0.04);
    scene.add(sprite, ring);
    bursts.push({ sprite, ring, height, t: 0 });
  }

  const crew = [0, 1, 2].map(() => {
    const tech = kit.person(scene, 0, 0, 0, "tech");
    tech.group.visible = false;
    return { ...tech, job: null };
  });
  const insideFloor = (v) => v.set(
    THREE.MathUtils.clamp(v.x, -floorW / 2 + 0.8, floorW / 2 - 0.8), 0, THREE.MathUtils.clamp(v.z, -floorD / 2 + 0.8, floorD / 2 - 0.8));

  function startResolve(name) {
    const isRobot = name === data.amr.name;
    const model = zones[name];
    const object = isRobot ? robot : model?.group;
    if (!object) return;
    const at = object.position.clone().setY(0);
    // Stand on the corridor side: in front of a machine, beside the kitchen pass or the robot.
    const dir = isRobot ? new THREE.Vector3(0, 0, 1)
      : model.front !== undefined ? new THREE.Vector3(0, 0, model.front) : new THREE.Vector3(1, 0, 0);
    const reach = isRobot ? 1.0 : (dir.z !== 0 ? info[name].d : info[name].w) / 2 + 0.45;
    const stand = insideFloor(at.clone().addScaledVector(dir, reach));
    const side = new THREE.Vector3(dir.z, 0, dir.x).multiplyScalar(Math.random() < 0.5 ? -4 : 4);
    const start = insideFloor(stand.clone().addScaledVector(dir, 2.2).add(side));
    const tickHeight = isRobot ? 1.4 : Math.min(model.height * 0.75, 2.4); // on the front of the machine
    const tech = crew.find((member) => member.job === null);
    if (!tech) { burstAt(at.clone().addScaledVector(dir, reach * 0.7), tickHeight); return; } // everyone is busy: just show the tick
    const walk = start.distanceTo(stand) / 1.7;
    const tickAt = at.clone().addScaledVector(dir, isRobot ? 0.4 : reach * 0.7); // just in front of it
    tech.job = { start, stand, at: tickAt, dir, walk, tickHeight, t: 0, ticked: false };
    tech.group.position.copy(start);
    tech.group.visible = true;
  }

  function stepCrew(time, dt) {
    for (const tech of crew) {
      const job = tech.job;
      if (!job) continue;
      job.t += dt;
      const { start, stand, walk } = job;
      const work = 1.8;
      let walking = true;
      if (job.t < walk) { // walking in
        tech.group.position.lerpVectors(start, stand, job.t / walk);
        tech.group.rotation.y = Math.atan2(stand.x - start.x, stand.z - start.z);
      } else if (job.t < walk + work) { // working on the machine
        walking = false;
        tech.group.position.copy(stand);
        tech.group.rotation.y = Math.atan2(-job.dir.x, -job.dir.z);
        tech.arms[1].rotation.x = -1.2 + 0.35 * Math.sin(time * 9);
      } else { // done: tick, then walk away
        if (!job.ticked) { job.ticked = true; burstAt(job.at, job.tickHeight); }
        const back = (job.t - walk - work) / walk;
        tech.group.position.lerpVectors(stand, start, Math.min(back, 1));
        tech.group.rotation.y = Math.atan2(start.x - stand.x, start.z - stand.z);
        if (back >= 1) { tech.job = null; tech.group.visible = false; }
      }
      const stride = walking ? Math.sin(time * 8) * 0.4 : 0;
      tech.legs[0].rotation.x = stride;
      tech.legs[1].rotation.x = -stride;
      tech.arms[0].rotation.x = -stride;
      if (walking) tech.arms[1].rotation.x = stride;
    }
    for (const burst of bursts.slice()) {
      burst.t += dt;
      const grow = Math.min(burst.t / 0.45, 1);
      const pop = 1 + 0.25 * Math.sin(Math.PI * grow) * (1 - grow); // slight overshoot
      const size = view.labelSize * 0.32 * grow * pop;
      burst.sprite.scale.set(size, size, 1);
      burst.sprite.position.y = burst.height + 0.35 * burst.t;
      const fade = burst.t < 1.3 ? 1 : Math.max(1 - (burst.t - 1.3) / 0.5, 0);
      burst.sprite.material.opacity = fade;
      burst.ring.scale.setScalar(1 + burst.t * 1.6);
      burst.ring.material.opacity = 0.8 * Math.max(1 - burst.t / 1.4, 0);
      if (burst.t > 1.8) {
        scene.remove(burst.sprite, burst.ring);
        bursts.splice(bursts.indexOf(burst), 1);
      }
    }
  }

  // ---- Selecting a zone: highlight, camera glide and inspector panel --------
  const canvas = renderer.domElement;
  const raycaster = new THREE.Raycaster();
  let sendToPython = () => {};
  let pressedAt = [0, 0];
  let selected = null; // name of the selected zone or robot
  let info = {}; // latest state from Python for every zone and the robot, by name
  let glide = null; // an in-progress camera move

  const hint = document.createElement("div");
  hint.className = "twin-hint";
  hint.innerHTML = '<span class="mi">ads_click</span>Click any machine to inspect it or simulate a fault';
  box.appendChild(hint);
  const panel = document.createElement("div");
  panel.className = "inspector";
  box.appendChild(panel);

  // ---- In-view controls: camera views, layers, legend and hover tooltip ------
  // Camera views: a fixed pose ([from, to]), or the name of a zone to select.
  const VIEWS = dining
    ? [["home", "chair", "Dining room"], ["Kitchen pass", "room_service", "Kitchen pass"], ["robot", "smart_toy", "Robot"]]
    : [["home", "home", "Whole kitchen"], ["cold", "ac_unit", "Cold rooms"], ["production", "conveyor_belt", "Production"], ["robot", "robot_2", "Robot"]];
  const POSES = {
    cold: [[-3.5, 9, 6.5], [-3.5, 0.8, -4.8]],
    production: [[0.6, 11, 17.5], [0.6, 0.4, 3.4]],
  };
  const LAYERS = [["status", "monitor_heart", "Status"], ["temperature", "thermostat", "Temperature"], ["safety", "health_and_safety", "Safety"]];
  let layer = "status";

  const tools = document.createElement("div");
  tools.className = "twin-tools";
  const button = ([key, iconName, text], group) =>
    `<button data-${group}="${escapeHtml(key)}" title="${text}"><span class="mi">${iconName}</span><span class="tool-text">${text}</span></button>`;
  tools.innerHTML =
    `<div class="tool-group">${VIEWS.map((v) => button(v, "view")).join("")}` +
    (data.fill ? button(["screen", "fullscreen", "Full screen"], "action") : "") + "</div>" +
    `<div class="tool-group">${LAYERS.map((l) => button(l, "layer")).join("")}</div>`;
  box.appendChild(tools);
  const legend = document.createElement("div");
  legend.className = "twin-legend";
  legend.innerHTML = '<b>Temperature vs safe limit</b><i></i><span>Safe</span><span>Near limit</span><span>Over</span>';
  box.appendChild(legend);
  const tip = document.createElement("div");
  tip.className = "twin-tip";
  box.appendChild(tip);

  function markActive() {
    tools.querySelectorAll("[data-layer]").forEach((b) => b.classList.toggle("on", b.dataset.layer === layer));
    legend.classList.toggle("show", layer === "temperature");
  }
  markActive();

  // The pose for a preset, backing off to fit the floor when the preset asks for it.
  function presetPose(preset) {
    const target = new THREE.Vector3(...preset.to);
    const direction = new THREE.Vector3(...preset.from).sub(target);
    let distance = direction.length();
    if (preset.fitWidth) {
      const halfWidthPerMetre = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect;
      distance = Math.max(distance, preset.fitWidth / 2 / halfWidthPerMetre);
    }
    return { pos: target.clone().add(direction.normalize().multiplyScalar(distance)), target };
  }
  function glideToPose({ pos, target }) {
    selected = null;
    renderPanel();
    glide = { t: 0, fromPos: camera.position.clone(), fromTarget: controls.target.clone(), toPos: pos, toTarget: target };
    viewerMoved = true;
  }

  tools.addEventListener("pointerup", (event) => {
    lastActivity = performance.now();
    // Full screen: the whole browser window, so only the twin page is visible (Esc to leave).
    if (event.target.closest("[data-action=screen]")) {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen?.();
    }
    const viewKey = event.target.closest("[data-view]")?.dataset.view;
    const layerKey = event.target.closest("[data-layer]")?.dataset.layer;
    if (layerKey) {
      layer = layerKey;
      markActive();
    }
    if (!viewKey) return;
    lastTouch = performance.now();
    if (viewKey === "home") glideToPose(presetPose(dining ? CAMERAS.dining : CAMERAS.overview));
    else if (viewKey === "robot") select(data.amr.name);
    else if (POSES[viewKey]) glideToPose({ pos: new THREE.Vector3(...POSES[viewKey][0]), target: new THREE.Vector3(...POSES[viewKey][1]) });
    else if (zones[viewKey]) select(viewKey);
  });
  for (const type of ["pointerdown", "wheel"]) tools.addEventListener(type, (event) => event.stopPropagation());

  // Colour scale for the temperature layer: green while safe, amber near the limit, red beyond it.
  const SAFE = new THREE.Color(0x17b26a), NEAR = new THREE.Color(0xf79009), OVER = new THREE.Color(0xd92d20);
  function heatColor(heat) {
    if (heat <= 0.6) return SAFE.clone();
    if (heat <= 0.85) return SAFE.clone().lerp(NEAR, (heat - 0.6) / 0.25);
    return NEAR.clone().lerp(OVER, Math.min((heat - 0.85) / 0.15, 1));
  }

  // Hover tooltip: the name and reading of whatever is under the pointer.
  function showTip(event, name) {
    const zone = name && name !== selected && info[name];
    if (!zone) { tip.classList.remove("show"); return; }
    const reading = name === data.amr.name ? zone.reading : zone.label;
    tip.innerHTML = `<b>${escapeHtml(name)}</b>${reading ? `<span>${escapeHtml(reading)}</span>` : ""}`;
    const area = box.getBoundingClientRect();
    tip.style.left = `${event.clientX - area.left + 14}px`;
    tip.style.top = `${event.clientY - area.top + 14}px`;
    tip.classList.add("show");
  }

  // Move the camera smoothly so it looks at `target` from `distance` away. The view is
  // nudged so the selected machine sits in the middle of the space right of the inspector
  // panel (about 330 px wide), whatever the width of the view.
  function glideTo(target, distance) {
    const offset = camera.position.clone().sub(controls.target).setLength(distance);
    const right = new THREE.Vector3().crossVectors(offset, camera.up).normalize().negate();
    const screenShift = Math.min(330 / (box.clientWidth || 900), 0.45); // in screen units, -1 to 1 across
    const halfWidth = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect * distance;
    const lookAt = target.clone().addScaledVector(right, -screenShift * halfWidth);
    glide = { t: 0, fromPos: camera.position.clone(), fromTarget: controls.target.clone(),
              toPos: lookAt.clone().add(offset), toTarget: lookAt };
    viewerMoved = true;
  }
  let home = null; // where the camera started, to return to on close

  function select(name) {
    if (!home) home = { pos: camera.position.clone(), target: controls.target.clone() };
    selected = name;
    const object = name === data.amr.name ? robot : zones[name].group;
    const target = object.position.clone().setY(0.8);
    // The dining room is smaller than the kitchen, so it needs a wider shot to keep its context.
    const [near, far] = dining ? [13, 19] : [9, 16];
    glideTo(target, Math.max(near, Math.min(far, camera.position.distanceTo(controls.target) * 0.65)));
    renderPanel();
  }

  function deselect() {
    selected = null;
    if (home) glide = { t: 0, fromPos: camera.position.clone(), fromTarget: controls.target.clone(),
                        toPos: home.pos.clone(), toTarget: home.target.clone() };
    renderPanel();
  }

  // A small line chart of the last 10 minutes, drawn as SVG for the inspector panel.
  function chartSvg(chart, alert) {
    const W = 262, H = 96, left = 34, right = 8, top = 10, bottom = 18;
    const { values, compare, limits, targets } = chart;
    const all = [...values, ...(compare || []), ...limits.map((l) => l[0]), ...targets.map((t) => t[0])];
    let lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo || 1) * 0.1;
    lo -= pad;
    hi += pad;
    const x = (i, n) => left + (i / Math.max(n - 1, 1)) * (W - left - right);
    const y = (v) => top + (1 - (v - lo) / (hi - lo)) * (H - top - bottom);
    const path = (series) => series.map((v, i) => `${i ? "L" : "M"}${x(i, series.length).toFixed(1)},${y(v).toFixed(1)}`).join("");
    const decimals = hi - lo < 12 ? 1 : 0;
    const color = alert ? "#d92d20" : "#2a78d6";
    const n = values.length;
    const reference = ([value, label], stroke) =>
      `<line x1="${left}" x2="${W - right}" y1="${y(value)}" y2="${y(value)}" stroke="${stroke}" stroke-width="1" stroke-dasharray="3 3"/>` +
      // Labelled at the left, away from "now" where a fault spikes, with a white halo to stay readable.
      `<text x="${left + 4}" y="${y(value) - 3}" fill="${stroke}" font-size="9" font-weight="600" stroke="#fff" stroke-width="3" paint-order="stroke">${escapeHtml(label)} ${value.toFixed(decimals)}</text>`;
    const last = values[n - 1];
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${escapeHtml(chart.title)}, last 10 minutes">` +
      `<line x1="${left}" x2="${W - right}" y1="${H - bottom}" y2="${H - bottom}" stroke="#e4e7ec"/>` +
      `<text x="${left - 4}" y="${top + 3}" text-anchor="end" fill="#98a2b3" font-size="9">${hi.toFixed(decimals)}</text>` +
      `<text x="${left - 4}" y="${H - bottom}" text-anchor="end" fill="#98a2b3" font-size="9">${lo.toFixed(decimals)}</text>` +
      `<text x="${left}" y="${H - 4}" fill="#98a2b3" font-size="9">−10 min</text>` +
      `<text x="${W - right}" y="${H - 4}" text-anchor="end" fill="#98a2b3" font-size="9">now</text>` +
      limits.map((l) => reference(l, "#d92d20")).join("") +
      targets.map((t) => reference(t, "#667085")).join("") +
      `<path d="${path(values)} L${x(n - 1, n)},${H - bottom} L${left},${H - bottom} Z" fill="${color}" fill-opacity="0.1"/>` +
      (compare ? `<path d="${path(compare)}" fill="none" stroke="#98a2b3" stroke-width="1.5" stroke-dasharray="4 3"/>` : "") +
      `<path d="${path(values)}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>` +
      `<circle cx="${x(n - 1, n)}" cy="${y(last)}" r="3.5" fill="${color}" stroke="#fff" stroke-width="1.5"/>` +
      `</svg>`;
  }

  // The panel shows the selected zone's live reading and its buttons.
  function renderPanel() {
    hint.classList.toggle("hidden", selected !== null);
    const zone = selected && info[selected];
    if (!zone) {
      panel.classList.remove("open");
      return;
    }
    const isRobot = selected === data.amr.name;
    const reading = isRobot ? zone.reading : zone.label;
    let status = '<span class="pill ok"><span class="mi">check_circle</span>Normal</span>';
    if (zone.alert || zone.blocked) status = '<span class="pill crit"><span class="mi">error</span>Alert</span>';
    else if (zone.busy) status = '<span class="pill warn"><span class="mi">schedule</span>Order waiting</span>';
    else if (zone.scenario?.active) status = '<span class="pill warn"><span class="mi">bolt</span>Fault starting</span>';

    let buttons = "";
    if (zone.scenario) {
      buttons += zone.scenario.active
        ? `<button class="insp-btn resolve" data-action="scenario"><span class="mi">task_alt</span>Resolve fault <small>· ${escapeHtml(zone.scenario.label)}</small></button>`
        : `<button class="insp-btn fault" data-action="scenario"><span class="mi">bolt</span>Simulate: ${escapeHtml(zone.scenario.label)}</button>`;
    } else {
      buttons += '<div class="insp-note">No demo fault for this zone</div>';
    }
    if (zone.has_page) {
      buttons += '<button class="insp-btn page" data-action="page">Open page<span class="mi">arrow_forward</span></button>';
    }
    const reading_html = reading
      ? `<div class="insp-reading"><span class="insp-value ${String(reading).length > 14 ? "small" : ""}">${escapeHtml(reading)}</span>${status}</div>`
      : `<div class="insp-reading"><span class="insp-value small">No live reading</span>${status}</div>`;
    const legend = zone.chart?.compare ? '<span class="insp-key"><i></i>Actual <i class="dash"></i>Recipe</span>' : "";
    const chart_html = zone.chart
      ? `<div class="insp-chart"><div class="insp-chart-head"><span>${escapeHtml(zone.chart.title)} · ${escapeHtml(zone.chart.unit)}</span>${legend}</div>` +
        `${chartSvg(zone.chart, zone.alert)}</div>`
      : "";
    const html =
      `<div class="insp-head"><div class="insp-icon ${zone.alert ? "alert" : ""}"><span class="mi">${ICONS[zone.kind] || "info"}</span></div>` +
      `<div><div class="insp-name">${escapeHtml(selected)}</div><div class="insp-sub">${escapeHtml(zone.subtitle)}</div></div>` +
      '<button class="insp-close" data-action="close" title="Close"><span class="mi">close</span></button></div>' +
      reading_html + chart_html + `<div class="insp-actions">${buttons}</div>`;
    if (html !== panel.innerHTML) panel.innerHTML = html; // rebuild only when something changed
    panel.classList.add("open");
  }

  // Act on pointer release rather than "click": the panel is redrawn as readings change,
  // and a click whose press and release land on different (redrawn) buttons would be lost.
  panel.addEventListener("pointerup", (event) => {
    lastActivity = performance.now();
    const action = event.target.closest("[data-action]")?.dataset.action;
    const zone = selected && info[selected];
    if (action === "close") deselect();
    if (action === "scenario" && zone?.scenario) sendToPython("scenario", zone.scenario.key);
    if (action === "page") sendToPython("clicked", selected);
  });
  // Keep drags and scrolls on the panel from moving the camera.
  for (const type of ["pointerdown", "wheel"]) panel.addEventListener(type, (event) => event.stopPropagation());

  function nameUnder(event) {
    const area = canvas.getBoundingClientRect();
    const pointer = new THREE.Vector2(
      ((event.clientX - area.left) / area.width) * 2 - 1,
      -((event.clientY - area.top) / area.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    let hit = raycaster.intersectObjects(clickable, true)[0]?.object;
    while (hit && !hit.userData.name) hit = hit.parent; // climb from the mesh to its zone
    return hit ? hit.userData.name : null;
  }
  canvas.addEventListener("pointerdown", (event) => (pressedAt = [event.clientX, event.clientY]));
  canvas.addEventListener("pointerup", (event) => {
    // A press that moved was a drag to rotate the view, not a click.
    const moved = Math.hypot(event.clientX - pressedAt[0], event.clientY - pressedAt[1]);
    if (moved >= 5) return;
    const name = nameUnder(event);
    if (name) select(name);
    else if (selected) deselect();
  });
  let hovered = null;
  let knownAlerts = null; // zones in alert at the last update (null until the first one)
  let lastTouch = -Infinity; // when the viewer last pressed on the 3D view
  let robotWasActive; // the robot's fault state at the last update, to spot a resolve
  let safetyFromSidebar = false;
  canvas.addEventListener("pointerdown", () => (lastTouch = lastActivity = performance.now()));
  canvas.addEventListener("pointermove", (event) => {
    hovered = nameUnder(event);
    canvas.style.cursor = hovered ? "pointer" : "grab";
    showTip(event, hovered);
  });
  canvas.addEventListener("pointerleave", () => {
    hovered = null;
    tip.classList.remove("show");
  });

  // ---- Apply new state from Python -----------------------------------------
  function update(state, setTriggerValue) {
    sendToPython = setTriggerValue;
    info = Object.fromEntries(state.zones.map((zone) => [zone.name, zone]));
    info[state.amr.name] = { ...state.amr, kind: state.amr.kind };
    const alerting = new Set();
    const resolved = new Set(); // fault keys resolved in this update (the pass and robot share one)
    for (const zone of state.zones) {
      const model = zones[zone.name];
      model.alert = zone.alert;
      model.busy = zone.busy;
      model.doorOpen = zone.door_open;
      model.heat = zone.heat ?? null;
      model.effects = new Set(zone.scenario?.active ? EFFECTS[zone.scenario.key] || [] : []);
      const active = !!zone.scenario?.active;
      if (model.wasActive && !active && !resolved.has(zone.scenario.key)) {
        resolved.add(zone.scenario.key);
        startResolve(zone.name);
      }
      model.wasActive = active;
      model.display?.(zone.kind === "quality" ? `PASS ${zone.label}` : zone.label, zone.alert);
      if (zone.alert) alerting.add(zone.name);
      if (model.dishes) model.dishes.visible = zone.served;
      // Labels show the short name: "Chiller 1 · Dim Sum" becomes "Chiller 1".
      model.setText(zone.name.split(" · ")[0], zone.door_open ? `${zone.label}, door open` : zone.label, zone.alert);
    }
    const robotActive = !!state.amr.scenario?.active;
    if (robotWasActive && !robotActive && !resolved.has(state.amr.scenario.key)) startResolve(state.amr.name);
    robotWasActive = robotActive;
    robotTarget.set(state.amr.x, 0, state.amr.z);
    robotBlocked = state.amr.blocked;
    obstacle.visible = robotBlocked;
    fallenCrate.visible = robotBlocked;
    if (robotBlocked) alerting.add(state.amr.name);
    safetyFromSidebar = state.safety_zones_visible;

    // Fly to a zone that has just gone into alert, unless the viewer is busy with the view.
    const fresh = [...alerting].filter((name) => knownAlerts !== null && !knownAlerts.has(name));
    knownAlerts = alerting;
    if (fresh.length && selected === null && performance.now() - lastTouch > 4000) select(fresh[0]);
    lamp.color.set(robotBlocked ? COLOR.alert : COLOR.ok);
    cargo.visible = state.amr.carrying;
    setRobotText(state.amr.name, robotBlocked ? "Blocked" : state.amr.label, robotBlocked);
    renderPanel();
  }

  // ---- Animation loop -------------------------------------------------------
  const padColor = new THREE.Color(COLOR.pad);
  const alertColor = new THREE.Color(COLOR.alert);
  const busyColor = new THREE.Color(COLOR.warm);
  const selectedColor = new THREE.Color(SELECTED);
  const timer = new THREE.Clock();
  let detachedFor = 0;

  function resize() {
    const width = box.clientWidth || 600;
    const height = box.clientHeight || data.height;
    box.classList.toggle("compact", width < 820);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    fitToWidth();
  }

  // Back the camera off along its line of sight until `fitWidth` metres fit across the view.
  function fitToWidth() {
    if (!view.fitWidth || viewerMoved) return;
    const target = new THREE.Vector3(...view.to);
    const direction = new THREE.Vector3(...view.from).sub(target);
    const halfWidthPerMetre = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect;
    const distance = Math.max(direction.length(), view.fitWidth / 2 / halfWidthPerMetre);
    const pos = target.clone().add(direction.normalize().multiplyScalar(distance));
    if (glide?.intro) glide.toPos.copy(pos); // the fly-in is still landing: move its end point
    else camera.position.copy(pos);
  }
  new ResizeObserver(resize).observe(box);
  resize();

  // ---- Opening fly-in and idle orbit ----------------------------------------
  // The whole-room views open with the camera sweeping down from high above, then the
  // labels fade in one by one. Left alone for a while, the camera slowly circles the room.
  const IDLE_ORBIT_S = 30;
  let introTime = null; // seconds since the fly-in started, or null when there is none
  let orbiting = false; // the idle sway is running
  let swayTime = 0, swayHome = null; // time into the sway, and the view it sways around
  if (view.fitWidth) {
    introTime = 0;
    const toPos = camera.position.clone(), toTarget = controls.target.clone();
    camera.position.set(toTarget.x, 46, toTarget.z + 4);
    glide = { t: 0, duration: 3.2, intro: true, fromPos: camera.position.clone(), fromTarget: toTarget.clone(), toPos, toTarget };
    labelSprites.forEach((sprite) => (sprite.material.opacity = 0));
  }

  function animate() {
    const dt = Math.min(timer.getDelta(), 0.1);
    // Stop and free the graphics context once the page has been left.
    detachedFor = box.isConnected ? 0 : detachedFor + dt;
    if (detachedFor > 3) {
      renderer.dispose();
      renderer.forceContextLoss();
      return;
    }
    requestAnimationFrame(animate);

    const pulse = 0.5 + 0.5 * Math.sin(timer.elapsedTime * 5);
    // Nothing comes through the line while the forming machine is jammed.
    const lineStopped = Object.values(zones).some((m) => m.kind === "forming" && (m.alert || m.effects.has("beacon")));
    if (flowStrip) {
      if (!lineStopped) flowStrip.material.map.offset.x -= dt * 1.1;
      flowStrip.material.color.set(lineStopped ? COLOR.alert : 0x17b26a);
    }
    for (const model of Object.values(zones)) {
      // Zones in alert pulse red; the rest settle back to normal.
      // Busy zones (a table waiting for food) get a steady orange floor.
      model.pad.color.copy(padColor).lerp(alertColor, model.alert ? 0.35 + 0.4 * pulse : 0);
      if (model.busy && !model.alert) model.pad.color.lerp(busyColor, 0.5);
      if (model.group.userData.name === selected) model.pad.color.lerp(selectedColor, 0.35 + 0.15 * pulse);
      else if (model.group.userData.name === hovered) model.pad.color.lerp(selectedColor, 0.15);
      for (const mat of model.glow) {
        mat.emissive.copy(alertColor);
        mat.emissiveIntensity = model.alert ? 0.15 + 0.35 * pulse : 0;
      }
      if (model.hinge) {
        const angle = model.doorOpen ? model.openAngle : 0;
        model.hinge.rotation.y += (angle - model.hinge.rotation.y) * Math.min(dt * 4, 1);
      }
      if (model.beam) model.beam.color.set(model.alert ? COLOR.alert : COLOR.ok);
      // Fault effects.
      const on = model.effects;
      model.andon?.(timer.elapsedTime, model.alert || on.has("beacon"));
      model.pinned.pin.visible = model.alert;
      // Red "!" while the fault is on; a green tick once it is fixed and readings are recovering.
      const pinMap = model.alert && !model.wasActive ? okPinTexture : pinTexture;
      if (model.pinned.pin.material.map !== pinMap) model.pinned.pin.material.map = pinMap;
      model.pinned.pin.position.y = model.pinned.y + 0.12 * Math.sin(timer.elapsedTime * 3);
      if (model.beacon) {
        model.beacon.beacon.visible = on.has("beacon");
        model.beacon.spinner.rotation.y += dt * 6;
      }
      if (model.smoke) { model.smoke.on = on.has("smoke"); model.smoke.step(dt); }
      if (model.mist) { model.mist.on = on.has("mist") && model.doorOpen; model.mist.step(dt); }
      if (model.heatHaze) { model.heatHaze.on = on.has("heat"); model.heatHaze.step(dt); }
      if (model.extra) {
        const scale = THREE.MathUtils.lerp(model.extra.scale.y, on.has("extra") ? 1 : 0.001, Math.min(dt * 5, 1));
        model.extra.scale.setScalar(scale);
        model.extra.visible = scale > 0.01;
      }
      if (model.rejects) {
        // Trays slide off the end of the line and drop into the reject bin.
        model.rejects.forEach((tray, i) => {
          tray.visible = on.has("rejects");
          const t = (timer.elapsedTime * 0.7 + i / model.rejects.length) % 1;
          const z = model.binZ * (0.2 + 0.75 * t) / 0.95;
          tray.position.set(model.binX - 0.1 + 0.1 * t, 1.0 - 0.75 * t * t + 0.25 * Math.sin(Math.PI * t) * (1 - t), z);
          tray.rotation.z = t * 1.2;
        });
      }
      // Temperature layer: colour each cold or hot zone by how close it is to its limit.
      if (model.baseColor) {
        if (layer === "temperature" && model.heat !== null) model.glow[0].color.copy(heatColor(model.heat));
        else model.glow[0].color.copy(model.baseColor);
      }
      if (model.pieces) {
        // Dim sum ride along the belt, and stop when the line is in alert or jammed.
        if (!model.alert && !on.has("beacon")) model.travelled += dt * 0.6;
        model.pieces.forEach((piece, i) => {
          const gap = model.pieceSpan / model.pieces.length;
          piece.position.x = model.pieceStart + ((model.travelled + i * gap) % model.pieceSpan);
        });
        // Every four pieces off the belt fill a steamer basket; a full stack of four is lidded and taken away.
        const passed = Math.floor((model.travelled * model.pieces.length) / model.pieceSpan);
        const filled = Math.floor(passed / 4) % 5;
        model.baskets.forEach((basket, i) => (basket.visible = i < filled));
        model.lid.visible = filled === 4;
      }
      if (model.trays) {
        // Trays ride through the inspection tunnel while product is coming down the line.
        if (!lineStopped) model.trayTravel = (model.trayTravel || 0) + dt * 0.45;
        model.trays.forEach((tray, i) => {
          tray.position.x = model.trayStart + (((model.trayTravel || 0) + (i * model.traySpan) / model.trays.length) % model.traySpan);
        });
      }
    }

    robotPin.pin.visible = robotBlocked;
    robotPin.pin.position.y = robotPin.y + 0.12 * Math.sin(timer.elapsedTime * 3);
    if (robotBlocked) lamp.color.set(Math.sin(timer.elapsedTime * 12) > 0 ? COLOR.alert : 0x330000);
    scene.getObjectByName("safety-zones").visible = safetyFromSidebar || layer === "safety";

    // The robot glides toward the latest position sent by Python.
    const step = robotTarget.clone().sub(robot.position);
    if (step.length() > 0.05) robotBody.rotation.y = Math.atan2(-step.z, step.x);
    robot.position.add(step.multiplyScalar(Math.min(dt * 1.5, 1)));
    if (spin && !robotBlocked) spin.rotation.y += dt * 9; // lidar turning while the robot drives
    for (const worker of staff) worker.animate(timer.elapsedTime, dt);
    stepCrew(timer.elapsedTime, dt);

    // Fade the labels in, one after another, once the fly-in has landed.
    if (introTime !== null) {
      introTime += dt;
      labelSprites.forEach((sprite, i) => {
        sprite.material.opacity = THREE.MathUtils.clamp((introTime - 2.4 - i * 0.07) / 0.5, 0, 1);
      });
      if (introTime > 3.2 + labelSprites.length * 0.07) introTime = null;
    }
    // Idle sway: nobody has touched the view for a while and nothing is selected.
    // Glide back to the whole-room view, then sway gently left and right around it,
    // so the kitchen always faces the audience (never a full circle round the back).
    const idle = Boolean(view.fitWidth) && selected === null && performance.now() - lastActivity > IDLE_ORBIT_S * 1000;
    if (idle && !orbiting && !glide) {
      orbiting = true;
      swayTime = 0;
      swayHome = presetPose(view);
      glide = { t: 0, duration: 2.4, fromPos: camera.position.clone(), fromTarget: controls.target.clone(),
                toPos: swayHome.pos.clone(), toTarget: swayHome.target.clone() };
    }
    if (!idle) orbiting = false;
    if (orbiting && !glide) {
      swayTime += dt;
      const angle = 0.35 * Math.sin(swayTime * 0.25); // about 20 degrees either side, one sway every 25 s
      const offset = swayHome.pos.clone().sub(swayHome.target).applyAxisAngle(camera.up, angle);
      camera.position.copy(swayHome.target).add(offset);
      controls.target.copy(swayHome.target);
    }

    if (glide) {
      glide.t = Math.min(glide.t + dt / (glide.duration || 0.8), 1);
      const ease = glide.intro ? 1 - Math.pow(1 - glide.t, 4) : 1 - Math.pow(1 - glide.t, 3);
      camera.position.lerpVectors(glide.fromPos, glide.toPos, ease);
      controls.target.lerpVectors(glide.fromTarget, glide.toTarget, ease);
      if (glide.intro) { // swing round while descending, so the fly-in sweeps rather than drops
        const swing = (1 - ease) * 1.1;
        const offset = camera.position.clone().sub(controls.target).applyAxisAngle(camera.up, swing);
        camera.position.copy(controls.target).add(offset);
      }
      if (glide.t === 1) glide = null;
    }

    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  return { update };
}
