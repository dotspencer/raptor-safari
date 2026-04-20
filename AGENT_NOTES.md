# Agent Notes

These notes document the fastest path we found for modifying gameplay values in this Unity WebGL build.

## Where To Look First

- `Build/rs.data.unityweb` is the most useful file for gameplay tuning.
- The round timer is not hardcoded in `Build/rs.wasm.unityweb`.
- The gameplay limit we changed lives in a serialized Unity `MonoBehaviour` inside the data bundle.
- Relevant script metadata shows a `GameLevel` class with a `gameLength` field.
- The metadata strings point at `Assets/_Scripts/Managers/GameLevel.cs`, which is a good clue even though the original source is not present here.

## Timer Change We Verified

- Original game duration: `240.0`
- Patched game duration: `500.0`
- The value was found in the `GameLevel` `MonoBehaviour` object with `path_id == 4627`.
- In that object's raw serialized payload, the float was at byte offset `32`.
- That exact object layout is version-specific, so treat the offset as a practical shortcut, not a universal rule.

## File Format Notes

- `Build/rs.data.unityweb` is a Brotli-compressed file.
- After decompression, the top-level file is a `UnityWebData1.0` container.
- That container includes several embedded files.
- The first entry is `data.unity3d`, which is the embedded `UnityFS` asset bundle.
- The `GameLevel` object was inside the `level2` serialized file within that bundle.
- The loader in this repo also accepts a valid uncompressed `UnityWebData1.0` container at the same path.

## Recommended Workflow

1. Decompress `Build/rs.data.unityweb` with `brotli -d`.
2. Parse the `UnityWebData1.0` header and extract the first entry, `data.unity3d`.
3. Open that embedded `UnityFS` bundle with `UnityPy`.
4. Find the `GameLevel` object and patch the raw float for `gameLength`.
5. Save the modified `UnityFS` bundle with the original compression settings.
6. Rebuild the outer `UnityWebData1.0` container, updating offsets and sizes for later entries.
7. Write the rebuilt `UnityWebData1.0` container back to `Build/rs.data.unityweb`.
8. Verify by reopening the rebuilt file and checking the same object again.

Current safest packaging choice:

- Leave `Build/rs.data.unityweb` uncompressed after rebuilding the container.
- This repo's loader successfully read the uncompressed container directly.
- Only recompress if you also reproduce Unity's `.unityweb` marker format correctly.

## Why Not Start With WAT

- Searching the WAT for `240.0` produced unrelated constants.
- The timer is data-driven, so wasm edits are a worse first move for values like round length.
- Use the wasm route only when the behavior is actually implemented in code rather than serialized content.

## Useful Clues For Future Tweaks

- Extracted metadata names are helpful for locating likely serialized gameplay values:
  - `GameLevel`
  - `gameLength`
  - `GlobalGame`
  - `EventManager`
  - `CarEventManager`
- If you are changing tuning values, inspect the Unity data bundle before touching wasm.
- If you are changing logic, UI flow, or engine behavior, then inspect the wasm and loader code.

## Practical Verification

- After patching, re-read the serialized object rather than trusting file sizes alone.
- We verified the final rebuilt file by reopening it and confirming `gameLength == 500.0`.
- A browser playthrough is still the final end-to-end check.

## Brotli Gotcha

- Do not assume the stock `brotli` CLI will recreate Unity's original `.unityweb` wrapper correctly.
- The original shipped file begins with Unity's Brotli marker string, not raw Brotli bytes.
- A plain CLI recompress removed that marker.
- When that happened, `Build/rs.loader.js` skipped decompression and tried to parse compressed bytes as `UnityWebData1.0`.
- The visible symptom was `Uncaught (in promise) RangeError: Maximum call stack size exceeded` around `rs.loader.js:2444`.
- That failure was a packaging issue, not a bad gameplay patch.

## Current Repo Context

- `package.json` only includes helper scripts for the wasm path:
  - `decompress`
  - `wasm2wat`
  - `wat2wasm`
- Those scripts are still useful for code edits, but not for simple data-driven gameplay tuning like the timer change above.
