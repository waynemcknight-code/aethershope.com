# aethershope.com

Elite Dangerous site for CMDR Aiether / fleet carrier *Aether's Hope* (G0N-GKG).

Hugo + [Congo](https://github.com/jpanther/congo) (git submodule), deployed to
GitHub Pages by Actions on push to `main`.

## Local build

```powershell
git submodule update --init --recursive   # required - see note below
hugo server -D
```

**The Congo submodule must be initialised.** Without it Hugo emits no error and
the home page renders to ~1 byte. Requires Hugo **extended** (installed at
`C:\Users\wayne\bin\hugo.exe`).

`static/CNAME` pins the custom domain - do not delete it, or Actions deploys
will silently revert the site to `*.github.io`.
