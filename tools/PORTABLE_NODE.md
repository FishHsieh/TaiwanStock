# Portable Node Runtime

This folder contains a copied Windows Node.js installation used by `run_bot.ps1`.

To refresh the bundle from the system Node install, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\sync_portable_node.ps1
```

You can also pass `-SourceDir` if you want to sync from a different Node installation.

The current bundled version is written to `tools/nodejs/VERSION.txt` after each sync.
