# Contributing to Worldlens

Contributions are welcome! A few guidelines:

- **Keep it keyless.** New data sources should be free and require no API key or account. If a key
  is unavoidable, make the feature opt-in and degrade gracefully when the key is absent.
- **Best-effort collectors.** Every feed is wrapped so one failure never breaks the snapshot.
- **No servers, no build step.** The globe is a single static HTML file; the collector is Python
  standard library only. Please keep it that way — it's a core feature.
- **Attribution.** If you add a library or dataset, add it to `CREDITS.md`.

### Adding a data source
1. Add a `get_*()` function in `collectors/worldlens_collector.py` (best-effort, returns a list/dict).
2. Wire it into `main()` and the snapshot.
3. Render it in `public/world-globe.html` as a new layer, and (optionally) a new lens.

### Adding a lens
Lenses are pure data — add an entry to the `LENSES` array in `world-globe.html` with the layer ids
it should isolate. That's it.
