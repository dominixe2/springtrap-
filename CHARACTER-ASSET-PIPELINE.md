# Character Asset Pipeline

This document defines how the Springtrap desktop prototype can grow into a multi-franchise character library without pretending that unbundled assets already exist.

## Scope

Initial franchises:
1. Five Nights at Freddy's (all games)
2. Apex Legends
3. Fortnite
4. VALORANT
5. Half-Life
6. Overwatch
7. Resident Evil
8. Cyberpunk 2077
9. DOOM
10. Mortal Kombat

## Asset rules

- Every character entry may reference a model, thumbnail, animation set, voice profile, and source/license notes.
- Do not bundle ripped game assets, copyrighted voice recordings, or unofficial uploads unless the project has permission to redistribute them.
- Prefer assets with clear reuse licenses, creator permission, or assets made specifically for this project.
- If no suitable asset is available, show a clearly labelled placeholder instead of claiming a finished 3D character exists.
- Keep model/animation/voice paths optional so the library still works while assets are being added.
- Character selection can change the Gemini role-play prompt independently of the rendered model.

## Suggested asset formats

- 3D model: glTF 2.0 / GLB for runtime loading where supported; Blender source (.blend) for editable project assets.
- Textures: PNG or JPEG, with source and license recorded.
- Animations: separate glTF animation clips or Blender actions, with standard names such as idle, walk, run, turn_left, turn_right, turn_around, talk, react.
- Voice: only recordings or voice models with documented permission; otherwise use a clearly labelled generic voice option or text-only output.
- Metadata: JSON manifest; every asset record includes origin, author, license, and verification status.

## Per-character manifest shape

```json
{
  "id": "fnaf.springtrap",
  "name": "Springtrap",
  "franchise": "Five Nights at Freddy's",
  "model": null,
  "thumbnail": null,
  "animations": {
    "idle": null,
    "walk": null,
    "turn_left": null,
    "turn_right": null,
    "turn_around": null,
    "talk": null,
    "react": null
  },
  "voice": {
    "mode": "text_or_configured_voice",
    "asset": null,
    "permission_verified": false
  },
  "asset_status": "placeholder",
  "source_url": null,
  "license": null,
  "notes": "Do not mark complete until the model and rights are verified."
}
```

## Implementation milestones

1. **Catalog:** stable IDs, franchises, character names, search, and selection.
2. **Asset manifest:** track actual models, thumbnails, animation clips, licenses, and missing assets.
3. **3D viewer:** load one verified GLB model and support orbit/rotation before adding desktop roaming.
4. **Animation controller:** idle, turn, talk, and reactions; use safe fallbacks when clips are absent.
5. **Voice layer:** separate Gemini response generation from TTS or licensed character recordings.
6. **Desktop integration:** transparent/always-on-top mode, user-controlled movement, and explicit permission before screen capture.
7. **Expansion:** add characters franchise by franchise, verifying every asset rather than downloading untrusted packs in bulk.

## Current status

The Windows app is still a Tkinter prototype. The existing character picker changes the conversational role only. It does not yet load 3D models, play character-specific animations, or provide original game voices. This file is a roadmap and asset contract, not evidence that those features are implemented.
