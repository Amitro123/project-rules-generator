# DXF Processing

**Project:** Slab3D Editor
**Category:** dxf
**Source:** Derived from README.md

## Purpose

Handle DXF file upload, validation, and SVG conversion for the kitchen granite
nesting workflow. DXF files represent measured stone pieces (sinks, countertops)
that must be rendered on a slab canvas for manual placement.

## Auto-Trigger

- Working on `/projects/{id}/dxf` endpoint
- Editing any file that imports `ezdxf`
- Implementing file upload or validation logic for `.dxf` files
- Converting DXF entities to SVG paths for Konva.js

## Guidelines

### Upload Endpoint Pattern

```python
from fastapi import UploadFile, HTTPException
import ezdxf
import io

@app.post("/projects/{project_id}/dxf")
async def upload_dxf(project_id: str, file: UploadFile):
    if not file.filename.endswith(".dxf"):
        raise HTTPException(400, "File must be a .dxf")

    content = await file.read()
    try:
        doc = ezdxf.read(io.StringIO(content.decode("utf-8")))
    except ezdxf.DXFError as e:
        raise HTTPException(422, f"Invalid DXF: {e}")

    # Extract modelspace entities for SVG conversion
    msp = doc.modelspace()
    # ... store to Supabase slab-files bucket
    return {"status": "ok", "entities": len(list(msp))}
```

### DXF → SVG Conversion

ezdxf has a built-in SVG backend. Prefer it over manual entity parsing:

```python
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.svg import SVGBackend
import io

def dxf_to_svg(doc) -> str:
    msp = doc.modelspace()
    backend = SVGBackend()
    frontend = Frontend(RenderContext(doc), backend)
    frontend.draw_layout(msp)
    return backend.get_string()
```

### Storage in Supabase

Store both the raw `.dxf` and the derived `.svg` in the `slab-files` bucket:

```python
supabase.storage.from_("slab-files").upload(
    f"projects/{project_id}/parts.dxf", content
)
supabase.storage.from_("slab-files").upload(
    f"projects/{project_id}/parts.svg", svg_content.encode()
)
```

Record the file in the `files` table with `file_type = 'dxf'`.

### Validation Rules

- Reject files > 10 MB (Supabase free tier storage limit consideration)
- Require at least one entity in modelspace (empty DXF = invalid)
- Warn if units are not `mm` — Slab3D uses millimetres throughout

## Error Handling

| Scenario | Response |
|---|---|
| Not a DXF file | HTTP 400 |
| Malformed DXF | HTTP 422 with ezdxf error detail |
| Empty modelspace | HTTP 422 "DXF contains no drawable entities" |
| Supabase upload fails | HTTP 502, log and retry once |

## Project Context (from README)

> **DXF Viewer**: SVG canvas (Konva.js)
> **Backend**: FastAPI + ezdxf + ReportLab
> Upload DXF → POST /projects/{id}/dxf
> `file_type CHECK (file_type IN ('dxf', 'slab', 'pdf'))`
