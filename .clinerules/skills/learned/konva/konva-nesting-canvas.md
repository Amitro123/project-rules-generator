# Konva.js Nesting Canvas

**Project:** Slab3D Editor
**Category:** canvas
**Source:** Derived from README.md

## Purpose

Implement the manual nesting UI — drag DXF-derived parts (stone pieces) over
a slab background image so the user can visually plan cut positions before
generating the PDF layout.

## Auto-Trigger

- Working on the nesting canvas component
- Editing files that import `konva` or `react-konva`
- Implementing drag-and-drop for DXF parts over slab images
- Building the `/slab` upload + crop rectangle flow

## Guidelines

### Stage Setup

```js
import Konva from "konva";

const stage = new Konva.Stage({
  container: "canvas-container",
  width: window.innerWidth,
  height: window.innerHeight,
});

// Layer 1: slab background image
const slabLayer = new Konva.Layer();
// Layer 2: draggable DXF parts
const partsLayer = new Konva.Layer();

stage.add(slabLayer);
stage.add(partsLayer);
```

### Load Slab Image as Background

```js
async function loadSlab(supabaseUrl) {
  return new Promise((resolve) => {
    const imageObj = new Image();
    imageObj.onload = () => {
      const slabImg = new Konva.Image({
        x: 0, y: 0,
        image: imageObj,
        width: stage.width(),
        height: stage.height(),
        listening: false, // background is not interactive
      });
      slabLayer.add(slabImg);
      slabLayer.draw();
      resolve(slabImg);
    };
    imageObj.src = supabaseUrl;
  });
}
```

### Render DXF Part as Draggable Shape

DXF parts arrive as SVG paths from the backend. Convert to Konva Path:

```js
function addPart(svgPathData, id) {
  const part = new Konva.Path({
    data: svgPathData,
    fill: "rgba(100, 160, 220, 0.5)",
    stroke: "#1a6fc4",
    strokeWidth: 1,
    draggable: true,
    id: id,
  });

  part.on("dragend", () => {
    savePlacement(id, part.x(), part.y(), part.rotation());
  });

  // Right-click to rotate 90deg
  part.on("contextmenu", (e) => {
    e.evt.preventDefault();
    part.rotation((part.rotation() + 90) % 360);
    partsLayer.draw();
  });

  partsLayer.add(part);
  partsLayer.draw();
}
```

### Save Placements to Backend

After each `dragend`, persist position so PDF generation can use it:

```js
async function savePlacement(partId, x, y, rotation) {
  await fetch(`/projects/${projectId}/placements`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    },
    body: JSON.stringify({ part_id: partId, x, y, rotation }),
  });
}
```

### Crop Rectangle for Slab Upload

When the user uploads a slab photo, let them draw a crop rect:

```js
let cropRect = null;
let drawing = false;
let startPos = {};

stage.on("mousedown", () => {
  if (mode !== "crop") return;
  drawing = true;
  startPos = stage.getPointerPosition();
  cropRect = new Konva.Rect({
    x: startPos.x, y: startPos.y,
    width: 0, height: 0,
    stroke: "red", strokeWidth: 2, dash: [6, 3],
  });
  slabLayer.add(cropRect);
});

stage.on("mousemove", () => {
  if (!drawing) return;
  const pos = stage.getPointerPosition();
  cropRect.width(pos.x - startPos.x);
  cropRect.height(pos.y - startPos.y);
  slabLayer.draw();
});

stage.on("mouseup", () => {
  drawing = false;
  // Send crop coords to POST /slab
});
```

## Key Constraints (from README)

- Manual nesting only — no auto-nesting algorithm in MVP
- Single admin user, no real-time collab
- Parts are DXF-derived SVG paths, not raster images
- Canvas must export placement data for `GET /pdf` to consume

## Project Context (from README)

> **DXF Viewer**: SVG canvas (Konva.js)
> Nesting canvas: Drag DXF parts over slab image
> Slab upload + crop rect → POST /slab
> "Generate PDF" → GET /pdf
