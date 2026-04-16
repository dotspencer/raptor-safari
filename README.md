<img width="700" height="500" alt="Screenshot 2026-04-16 at 12 04 59 PM" src="https://github.com/user-attachments/assets/7e4ef28b-54f2-462c-a406-9501594de744" />

# Off-Road Velociraptor Safari (WebGL)

Unity WebGL build mirrored from [blurst.com/raptor-safari](https://blurst.com/raptor-safari). The game must be served over **HTTP**; opening `index.html` via `file://` will not load WebAssembly reliably.

## Run locally

From this directory:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open **http://127.0.0.1:8765/** in your browser.

Other static servers work the same way, for example:

```bash
npx serve -l 8765
```

Stop the server with **Ctrl+C** when you are done.
