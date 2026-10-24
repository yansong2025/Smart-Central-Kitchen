// 3D digital twins (the kitchen, and the restaurant dining room), drawn with three.js.
//
// Python (twin/__init__.py) sends the full state on every refresh: the zones
// with their label and alert flag, and the robot position. This file only
// draws that state. It builds the scene once, then updates it in place so the
// camera stays where the viewer left it.

const VENDOR = new URL("app/static/vendor/", document.baseURI).href;

const COLOR = {
  background: 0xf4f2ee, floor: 0xe6e2d9, pad: 0xfaf8f4, wall: 0xf0ede6,
  cold: 0xd5e4ee, steel: 0xc3c8ce, dark: 0x3d4046, belt: 0x55595f,
  crate: 0xc9a66b, dough: 0xfdf6e3, warm: 0xeb6834, accent: 0x9b1c1c,
  alert: 0xd03b3b, ok: 0x0ca30c,
  cloth: 0xfbf7ee, wood: 0x8a5a36, basket: 0xd9b77e, roast: 0x8a4b1f, white: 0xf3f3f1,
};
const SHIRTS = [0x5b7fa6, 0xa65b5b, 0x6b8f71, 0xb08a4f]; // guests' clothes

// Starting camera for each page: where it stands, what it looks at, and how big labels are.
// Close-ups hide the robot's label, which would fill the view when it drives past.
const CAMERAS = {
  overview: { from: [0, 19, 21], to: [0, 0, -1.2], labelSize: 3.9 },
  cold_rooms: { from: [0, 9, 8.5], to: [0, 1.2, -4.5], labelSize: 3.0 },
  amr: { from: [0, 26, 13], to: [0, 0, -0.8], labelSize: 3.3 },
  forming: { from: [-0.4, 4.6, 13.2], to: [-0.4, 0.9, 5.5], labelSize: 2.2, hideRobotLabel: true },
  oven: { from: [5.9, 4.5, 2.2], to: [5.9, 1.5, -5.5], labelSize: 2.2, hideRobotLabel: true },
  dining: { from: [0, 11.8, 10.4], to: [0, 0, -0.2], labelSize: 1.6 },
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

  // ---- Renderer, camera, lights -------------------------------------------
  const box = document.createElement("div");
  box.style.cssText = `width:100%;height:${data.height}px;border-radius:10px;overflow:hidden;`;
  parent.appendChild(box);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  box.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COLOR.background);

  const view = CAMERAS[data.focus] || CAMERAS.overview;
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  camera.position.set(...view.from);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(...view.to);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI * 0.47; // never look from below the floor
  controls.minDistance = 6;
  controls.maxDistance = 60;

  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d2c4, 1.5));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8);
  sun.position.set(8, 20, 12);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 18, bottom: -18 });
  scene.add(sun);

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
  function makeLabel(y, group) {
    const canvas = document.createElement("canvas");
    canvas.width = 360;
    canvas.height = 150;
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false }));
    sprite.scale.set(view.labelSize, view.labelSize * canvas.height / canvas.width, 1);
    sprite.position.y = y;
    sprite.renderOrder = 10;
    group.add(sprite);

    let shown = "";
    return function setText(title, detail, alert) {
      const text = `${title}|${detail}|${alert}`;
      if (text === shown) return;
      shown = text;
      const pen = canvas.getContext("2d");
      pen.clearRect(0, 0, canvas.width, canvas.height);
      pen.fillStyle = "rgba(255,255,255,0.94)";
      pen.strokeStyle = alert ? "#d03b3b" : "#cfcabd";
      pen.lineWidth = alert ? 8 : 3;
      pen.beginPath();
      pen.roundRect(6, 6, canvas.width - 12, canvas.height - 12, 24);
      pen.fill();
      pen.stroke();
      pen.textAlign = "center";
      pen.fillStyle = "#1f1d1a";
      pen.font = "600 42px system-ui, sans-serif";
      pen.fillText(title, canvas.width / 2, detail ? 64 : 90, canvas.width - 36);
      if (detail) {
        pen.font = "40px system-ui, sans-serif";
        pen.fillText((alert ? "⚠ " : "") + detail, canvas.width / 2, 116, canvas.width - 36);
      }
      texture.needsUpdate = true;
    };
  }

  // ---- Floor and walls ------------------------------------------------------
  const { width: floorW, depth: floorD } = data.floor;
  const floor = addBox(floorW, 0.2, floorD, material(data.floor.color || COLOR.floor), 0, -0.1, 0, scene);
  floor.castShadow = false;
  const wall = material(COLOR.wall);
  addBox(floorW, 3, 0.2, wall, 0, 1.5, -floorD / 2, scene);
  addBox(0.2, 3, floorD, wall, -floorW / 2, 1.5, 0, scene);
  addBox(0.2, 3, floorD, wall, floorW / 2, 1.5, 0, scene);

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

  // ---- One simple model per kind of zone -----------------------------------
  // Each builder gets the zone's group and `front`: +1 or -1, the side facing
  // the corridor. It returns the parts that update() and animate() change.
  const builders = {
    cold_room(zone, group, front) {
      const body = material(COLOR.cold);
      addBox(zone.w - 0.5, 2.4, zone.d - 0.6, body, 0, 1.2, 0, group);
      addBox(1.0, 0.35, 0.8, material(COLOR.steel), 0.6, 2.58, 0, group); // compressor
      const face = front * (zone.d - 0.6) / 2;
      addBox(1.2, 2.0, 0.04, material(COLOR.dark), 0, 1.0, face + front * 0.01, group); // doorway
      const hinge = new THREE.Group();
      hinge.position.set(-0.6, 0, face + front * 0.06);
      group.add(hinge);
      addBox(1.2, 2.0, 0.08, material(COLOR.steel, { metalness: 0.4 }), 0.6, 1.0, 0, hinge);
      return { height: 2.8, glow: [body], hinge, openAngle: -front * 1.9 };
    },
    oven(zone, group, front) {
      const body = material(COLOR.dark, { metalness: 0.3 });
      addBox(zone.w - 0.8, 2.2, zone.d - 1.4, body, 0, 1.1, 0, group);
      const fire = material(COLOR.warm, { emissive: COLOR.warm, emissiveIntensity: 0.9 });
      addBox(1.5, 0.9, 0.06, fire, 0, 1.2, front * ((zone.d - 1.4) / 2 + 0.02), group); // window
      addMesh(new THREE.CylinderGeometry(0.22, 0.22, 1.0), material(COLOR.steel), 0.8, 2.7, -front * 0.5, group);
      const face = front * ((zone.d - 1.4) / 2 + 0.08);
      for (const x of [-0.45, 0, 0.45]) { // ducks hanging in the window
        addMesh(new THREE.SphereGeometry(0.15), material(COLOR.roast), x, 1.2, face, group).scale.set(0.8, 1.5, 0.5);
      }
      addBox(1.5, 0.06, 0.06, material(COLOR.steel, { metalness: 0.5 }), 0, 0.62, face + front * 0.06, group); // door handle
      addBox(0.5, 0.3, 0.05, material(COLOR.ok, { emissive: COLOR.ok, emissiveIntensity: 0.5 }), -1.0, 1.85, face - front * 0.04, group); // control screen
      return { height: 2.9, glow: [body] };
    },
    hot_cabinet(zone, group, front) {
      const body = material(COLOR.steel, { metalness: 0.4 });
      addBox(zone.w - 1.0, 1.9, zone.d - 1.8, body, 0, 0.95, 0, group);
      const glass = material(COLOR.warm, { emissive: COLOR.warm, emissiveIntensity: 0.35 });
      addBox(zone.w - 1.4, 1.3, 0.06, glass, 0, 1.05, front * ((zone.d - 1.8) / 2 + 0.02), group);
      return { height: 2.6, glow: [body] };
    },
    forming(zone, group) {
      const span = zone.w - 0.8;
      addBox(span, 0.12, 0.9, material(COLOR.belt), 0, 0.9, 0, group); // conveyor belt
      addBox(span - 0.4, 0.8, 0.5, material(COLOR.steel), 0, 0.42, 0, group);
      const machine = material(COLOR.steel, { metalness: 0.4 });
      addBox(1.5, 1.5, 1.5, machine, -span / 2 + 0.9, 1.7, 0, group);
      addMesh(new THREE.CylinderGeometry(0.55, 0.25, 0.7), material(COLOR.accent), -span / 2 + 0.9, 2.8, 0, group); // hopper
      addBox(0.5, 0.3, 0.05, material(COLOR.ok, { emissive: COLOR.ok, emissiveIntensity: 0.5 }), -span / 2 + 0.9, 1.9, 0.78, group); // control screen
      const roller = addMesh(new THREE.CylinderGeometry(0.14, 0.14, 0.9), material(COLOR.steel, { metalness: 0.5 }), -span / 2 + 1.95, 1.22, 0, group);
      roller.rotation.x = Math.PI / 2;
      for (let i = 0; i < 3; i++) { // steamer baskets waiting at the end of the belt
        addMesh(new THREE.CylinderGeometry(0.34, 0.34, 0.16), material(COLOR.basket), span / 2 - 0.4, 1.05 + i * 0.17, 0, group);
      }
      const dough = material(COLOR.dough);
      const pieces = [...Array(7)].map(() => addMesh(new THREE.SphereGeometry(0.16), dough, 0, 1.08, 0, group));
      return { height: 3.6, glow: [machine], pieces, pieceStart: -span / 2 + 2.2, pieceSpan: span - 3.1 };
    },
    quality(zone, group) {
      const span = zone.w - 0.8;
      addBox(span, 0.12, 0.9, material(COLOR.belt), 0, 0.9, 0, group);
      addBox(span - 0.4, 0.8, 0.5, material(COLOR.steel), 0, 0.42, 0, group);
      const frame = material(COLOR.steel, { metalness: 0.4 });
      addBox(0.12, 2.3, 0.12, frame, 0, 1.15, -0.7, group); // camera gantry
      addBox(0.12, 2.3, 0.12, frame, 0, 1.15, 0.7, group);
      addBox(0.12, 0.12, 1.52, frame, 0, 2.3, 0, group);
      addBox(0.4, 0.3, 0.4, material(COLOR.dark), 0, 2.1, 0, group); // camera
      const beam = new THREE.MeshBasicMaterial({ color: COLOR.ok, transparent: true, opacity: 0.25 });
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.5, 1.0, 24, 1, true), beam);
      cone.position.set(0, 1.46, 0);
      group.add(cone);
      return { height: 3.1, glow: [frame], beam };
    },
    prep(zone, group) {
      const top = material(COLOR.steel, { metalness: 0.4 });
      for (const x of [-1.0, 1.0]) {
        addBox(1.5, 0.08, 2.4, top, x, 0.9, 0, group);
        addBox(1.3, 0.86, 2.2, material(COLOR.wall), x, 0.43, 0, group);
      }
      return { height: 1.9, glow: [top] };
    },
    table(zone, group) {
      addMesh(new THREE.CylinderGeometry(0.7, 0.7, 0.08, 32), material(COLOR.cloth), 0, 0.76, 0, group);
      addMesh(new THREE.CylinderGeometry(0.1, 0.25, 0.72), material(COLOR.wood), 0, 0.36, 0, group);
      for (let i = 0; i < 4; i++) {
        // Chairs sit on the diagonals, leaving the sides free for the robot.
        const seat = new THREE.Group();
        seat.rotation.y = Math.PI / 4 + i * Math.PI / 2;
        group.add(seat);
        addBox(0.42, 0.08, 0.42, material(COLOR.wood), 1.0, 0.45, 0, seat);
        addBox(0.06, 0.55, 0.42, material(COLOR.wood), 1.2, 0.72, 0, seat);
        if (i < zone.guests) {
          addMesh(new THREE.CylinderGeometry(0.17, 0.2, 0.55), material(SHIRTS[i]), 1.0, 0.77, 0, seat);
          addMesh(new THREE.SphereGeometry(0.15), material(0xe8c39e), 1.0, 1.2, 0, seat);
        }
      }
      const dishes = new THREE.Group(); // steamer baskets, shown once the table has its food
      group.add(dishes);
      for (const [x, z] of [[-0.25, -0.1], [0.22, -0.2], [0.05, 0.28]]) {
        addMesh(new THREE.CylinderGeometry(0.17, 0.17, 0.12), material(COLOR.basket), x, 0.86, z, dishes);
      }
      return { height: 1.2, glow: [], dishes };
    },
    pass(zone, group) {
      const counter = material(COLOR.steel, { metalness: 0.4 });
      addBox(1.0, 1.0, zone.d - 0.4, counter, 0, 0.5, 0, group);
      const heat = material(COLOR.warm, { emissive: COLOR.warm, emissiveIntensity: 0.8 });
      addBox(0.3, 0.08, zone.d - 0.8, heat, 0, 1.75, 0, group); // heat lamp over the pass
      for (const z of [-(zone.d - 0.9) / 2, (zone.d - 0.9) / 2]) addBox(0.08, 0.75, 0.08, counter, 0, 1.37, z, group);
      for (const z of [-0.9, 0, 0.9]) {
        addMesh(new THREE.CylinderGeometry(0.2, 0.2, 0.14), material(COLOR.basket), 0, 1.07, z, group);
      }
      return { height: 2.1, glow: [counter] };
    },
    dock(zone, group) {
      const crate = material(COLOR.crate);
      addBox(2.4, 0.15, 2.4, material(COLOR.belt), 0, 0.08, 0, group); // pallet
      addBox(1.0, 0.8, 1.0, crate, -0.6, 0.55, -0.5, group);
      addBox(1.0, 0.8, 1.0, crate, 0.6, 0.55, -0.5, group);
      addBox(1.0, 0.8, 1.0, crate, -0.6, 0.55, 0.6, group);
      addBox(1.0, 0.8, 1.0, crate, 0, 1.35, -0.5, group);
      return { height: 2.4, glow: [] };
    },
  };

  const zones = {};
  const clickable = []; // groups that open a page when clicked
  for (const zone of data.zones) {
    const group = new THREE.Group();
    group.position.set(zone.x, 0, zone.z);
    group.userData.name = zone.name;
    if (zone.clickable) clickable.push(group);
    scene.add(group);
    const pad = material(COLOR.pad);
    addBox(zone.w - 0.15, 0.06, zone.d - 0.15, pad, 0, 0.03, 0, group).castShadow = false;
    const parts = builders[zone.kind](zone, group, zone.z < 0 ? 1 : -1);
    zones[zone.name] = { ...parts, pad, setText: makeLabel(parts.height + 0.5, group), alert: false, busy: false, doorOpen: false, travelled: 0 };
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
  if (data.amr.clickable) clickable.push(robot);
  scene.add(robot);
  const robotBody = new THREE.Group(); // turns to face the direction of travel (+x is forward)
  robot.add(robotBody);
  const lamp = new THREE.MeshBasicMaterial({ color: COLOR.ok });

  // Each robot model returns `cargo` (what it carries) and its label height.
  const robotModels = {
    amr() { // low tray carrier used in the kitchen
      addBox(1.0, 0.3, 0.7, material(COLOR.dark), 0, 0.25, 0, robotBody);
      addBox(0.9, 0.06, 0.6, material(COLOR.accent), 0, 0.43, 0, robotBody);
      addMesh(new THREE.SphereGeometry(0.09), lamp, 0.42, 0.52, 0, robotBody);
      return { cargo: addBox(0.6, 0.35, 0.45, material(COLOR.crate), 0, 0.63, 0, robotBody), labelY: 2.4 };
    },
    server() { // tall serving robot with three trays and a face, used in the dining room
      addMesh(new THREE.CylinderGeometry(0.34, 0.38, 0.28, 24), material(COLOR.dark), 0, 0.14, 0, robotBody);
      addBox(0.1, 1.25, 0.5, material(COLOR.white), -0.26, 0.9, 0, robotBody); // spine
      for (const y of [0.5, 0.88, 1.26]) {
        addMesh(new THREE.CylinderGeometry(0.33, 0.33, 0.04, 24), material(COLOR.white), 0, y, 0, robotBody);
      }
      addBox(0.12, 0.3, 0.5, material(COLOR.dark), -0.2, 1.68, 0, robotBody); // screen "face"
      for (const z of [-0.11, 0.11]) addMesh(new THREE.SphereGeometry(0.045), lamp, -0.13, 1.7, z, robotBody);
      const cargo = new THREE.Group();
      robotBody.add(cargo);
      addMesh(new THREE.CylinderGeometry(0.2, 0.2, 0.13), material(COLOR.basket), 0.05, 1.35, 0, cargo);
      addMesh(new THREE.CylinderGeometry(0.2, 0.2, 0.13), material(COLOR.basket), 0.05, 0.97, 0, cargo);
      return { cargo, labelY: 2.5 };
    },
  };
  const { cargo, labelY } = robotModels[data.amr.kind]();
  const obstacle = addMesh(new THREE.ConeGeometry(0.25, 0.7, 16), material(COLOR.warm), 1.1, 0.35, 0, robotBody);
  const setRobotText = view.hideRobotLabel ? () => {} : makeLabel(labelY, robot);
  const robotTarget = robot.position.clone();
  let robotBlocked = false;

  // ---- Clicks: tell Python which zone was clicked, and it opens that page ----
  const canvas = renderer.domElement;
  const raycaster = new THREE.Raycaster();
  let sendToPython = () => {};
  let pressedAt = [0, 0];

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
    const name = moved < 5 ? nameUnder(event) : null;
    if (name) sendToPython("clicked", name);
  });
  canvas.addEventListener("pointermove", (event) => {
    canvas.style.cursor = nameUnder(event) ? "pointer" : "grab";
  });

  // ---- Apply new state from Python -----------------------------------------
  function update(state, setTriggerValue) {
    sendToPython = setTriggerValue;
    scene.getObjectByName("safety-zones").visible = state.safety_zones_visible;
    for (const zone of state.zones) {
      const model = zones[zone.name];
      model.alert = zone.alert;
      model.busy = zone.busy;
      model.doorOpen = zone.door_open;
      if (model.dishes) model.dishes.visible = zone.served;
      // Labels show the short name: "Chiller 1 · Dim Sum" becomes "Chiller 1".
      model.setText(zone.name.split(" · ")[0], zone.door_open ? `${zone.label}, door open` : zone.label, zone.alert);
    }
    robotTarget.set(state.amr.x, 0, state.amr.z);
    robotBlocked = state.amr.blocked;
    obstacle.visible = robotBlocked;
    lamp.color.set(robotBlocked ? COLOR.alert : COLOR.ok);
    cargo.visible = state.amr.carrying;
    setRobotText(state.amr.name, robotBlocked ? "Blocked" : state.amr.label, robotBlocked);
  }

  // ---- Animation loop -------------------------------------------------------
  const padColor = new THREE.Color(COLOR.pad);
  const alertColor = new THREE.Color(COLOR.alert);
  const busyColor = new THREE.Color(COLOR.warm);
  const timer = new THREE.Clock();
  let detachedFor = 0;

  function resize() {
    const width = box.clientWidth || 600;
    renderer.setSize(width, data.height);
    camera.aspect = width / data.height;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(box);
  resize();

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
    for (const model of Object.values(zones)) {
      // Zones in alert pulse red; the rest settle back to normal.
      // Busy zones (a table waiting for food) get a steady orange floor.
      model.pad.color.copy(padColor).lerp(alertColor, model.alert ? 0.35 + 0.4 * pulse : 0);
      if (model.busy && !model.alert) model.pad.color.lerp(busyColor, 0.5);
      for (const mat of model.glow) {
        mat.emissive.copy(alertColor);
        mat.emissiveIntensity = model.alert ? 0.15 + 0.35 * pulse : 0;
      }
      if (model.hinge) {
        const angle = model.doorOpen ? model.openAngle : 0;
        model.hinge.rotation.y += (angle - model.hinge.rotation.y) * Math.min(dt * 4, 1);
      }
      if (model.beam) model.beam.color.set(model.alert ? COLOR.alert : COLOR.ok);
      if (model.pieces) {
        // Dim sum ride along the belt, and stop when the line is in alert.
        if (!model.alert) model.travelled += dt * 0.6;
        model.pieces.forEach((piece, i) => {
          const gap = model.pieceSpan / model.pieces.length;
          piece.position.x = model.pieceStart + ((model.travelled + i * gap) % model.pieceSpan);
        });
      }
    }

    // The robot glides toward the latest position sent by Python.
    const step = robotTarget.clone().sub(robot.position);
    if (step.length() > 0.05) robotBody.rotation.y = Math.atan2(-step.z, step.x);
    robot.position.add(step.multiplyScalar(Math.min(dt * 1.5, 1)));

    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  return { update };
}
