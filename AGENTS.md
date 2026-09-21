# vantage6

Privacy-preserving federated learning infrastructure. Python 3.13 monorepo managed by `uv`, built with `hatchling`.

## AI Agent Rules

- **After every Python code change**: run `ruff format .` to apply formatting
- **Keep docstrings and comments to a minimum** — as concise as possible; explain only what the code cannot say for itself, never restate the signature or narrate the obvious
- **Never reference issues in code** — no issue, ticket, or PR numbers (and no links to them) in comments or docstrings
- **Never run `kubectl`** — K8s cluster state is outside the agent's scope, unless explicitly asked to do so
- **Never run `devspace` or `v6 dev` commands** — these should be user controlled
- **Never run `v6 sandbox` commands** — these spin up Docker infrastructure
- **Never modify `uv.lock` directly** — always regenerate through `make lock`
- **Never run `make image` or `make publish`** — builds and releases are deliberate, user-initiated actions
- **Never commit changes unless explicitly asked** — always present diffs for review first

## Packages (8 PyPI + 1 Angular UI)

All Python packages install under the `vantage6.*` namespace:

| Directory | PyPI name | Installed as | Role |
|---|---|---|---|
| `vantage6/` | `vantage6` | `vantage6.cli` | CLI (`v6` command) |
| `vantage6-common/` | `vantage6-common` | `vantage6.common` | Shared utilities |
| `vantage6-client/` | `vantage6-client` | `vantage6.client` | Python client library |
| `vantage6-algorithm-tools/` | `vantage6-algorithm-tools` | `vantage6.algorithm.tools` | Algorithm dev tools |
| `vantage6-backend-common/` | `vantage6-backend-common` | `vantage6.backend.common` | Shared by HQ + store |
| `vantage6-hq/` | `vantage6-hq` | `vantage6.hq` | HQ (headquarters server) |
| `vantage6-node/` | `vantage6-node` | `vantage6.node` | Node (runs at data sites) |
| `vantage6-algorithm-store/` | `vantage6-algorithm-store` | `vantage6.algorithm.store` | Algorithm store server |
| `vantage6-ui/` | — | — | Angular 22 web app |

Each `pyproject.toml` maps source via hatch, so e.g. `vantage6-hq/vantage6/hq/` becomes `vantage6.hq` when installed.

**HQ, node and algorithm store are delivered as Docker images, the common packages are (common) dependencies for the other packages. Only the vantage6 package from pypi is intended for end users. The vantage6-algorithm-tools package is intalled by algorithm developers and by images that contain algorithms.**

## Setup and Development Commands

```bash
# Editable install of all workspace packages with dev dependencies
make install-dev

# Non-editable install (uses uv.lock)
make install

# After changing any pyproject.toml dependencies
make lock

# Update lock and upgrade dependency versions
make lock-upgrade
```

## Code Quality

```bash
# Lint (CI runs these)
ruff check .
ruff format --check .

# Fix formatting
ruff format .

# Install pre-commit hook (runs on each commit)
pre-commit install

# Run manually against all files
pre-commit run --all-files
```

Ruff isort has custom sections: `v6-common`, `v6-client`, `v6-algo-tools`, `v6-cli`, `v6-backend-common`. Imports from `vantage6.common` go in `v6-common`, etc.

## Tests

Primary framework is **unittest**, run via custom runner `utest.py`:

```bash
# Run all tests with coverage
make test

# Run specific packages (comma-separated)
make test TEST_SUBPACKAGES=hq,common

# Run specific test suites directly
python utest.py --hq
python utest.py --common --cli
python utest.py --all

# Available flags: --common --cli --hq --node --algorithm-store --algorithm-tools --all
```

`utest.py` monkey-patches `uwsgi` as a dummy module (C extension only available in Docker). pytest is listed as a dev dependency but not used in CI or the test runner.

For external database tests, start databases with `docker compose -f testing/external-databases/docker-compose.yml up`.

## Local K8s Development (DevSpace)

Full local dev environment runs on Kubernetes with hot-reload. Requires [DevSpace](https://www.devspace.sh/), `kubectl`, and a local K8s distribution (microk8s, minikube, or Docker Desktop).

```bash
# Start dev environment (hub + nodes, prompts for populate)
v6 dev start

# Stop dev environment (keeps local data)
v6 dev stop

# Delete all k8s resources and local data
v6 dev clean

# Rebuild images (use --hq, --node, --store, --ui for specific)
v6 dev rebuild
v6 dev rebuild --hq
```

DevSpace deploys via Helm charts in `charts/`. Services expose:
- UI: `localhost:7600`
- HQ: `localhost:7601`
- Algorithm store: `localhost:7602`
- Keycloak (auth): `localhost:7680`
- HQ DB: `localhost:7632`
- Store DB: `localhost:7633`

Hot-reload behaviour differs: HQ and store use file sync + dev scripts. Node requires container restart on upload.

## Quick Sandbox

```bash
# Requires Docker, Docker login to dhi.io registry
v6 sandbox new    # creates hub + 3 nodes
v6 sandbox start
v6 sandbox stop
v6 sandbox remove
```

Default credentials: `admin` / `admin`. UI at `http://localhost:30760`.

## Docker Image Building

```bash
make image                    # node + HQ
make algorithm-store-image    # algorithm store
make ui-image                 # UI
```

Default registry: `ghcr.io/vantage6/infrastructure`. Override with `REGISTRY=`, `TAG=`.

## UI (Angular)

Work from `vantage6-ui/` directory:

```bash
cd vantage6-ui
npm run build
npm test
npm run lint
npm run format
```

Uses Keycloak for auth, Socket.IO for real-time communication.

## Documentation

Source lives in `docs/`, built with Sphinx. Requires Java for PlantUML diagrams.

```bash
# Install docs dependencies (run once, after make install-dev)
make install-docs

# Build static HTML
make html          # run from docs/

# Build with auto-refresh on http://127.0.0.1:8000
make devdocs        # watches .rst files and docstrings
make devdocs FUNCTIONDOCS=true  # include API docs (slower)
```

## Contributing

### Fork and branch workflow

```bash
# Fork the repo, then clone and add fork remote
git clone https://github.com/vantage6/vantage6
cd vantage6
git remote add fork https://github.com/{username}/vantage6

# Branch from latest main
git fetch origin
git checkout -b your-branch-name origin/main

# Push and create PR
git push --set-upstream fork your-branch-name
```

### Running a specific test

```bash
python -m unittest tests_folder.test_filename.TestClassName.test_name
```

Run from the directory above `tests_folder`.

### PR merge requirements

- At least one approved review from a code owner
- Unit tests, CodeQL (vulnerability scanning), and Codacy (code quality) must pass
- Coveralls coverage must not decrease

### Testing CLI changes locally

Use `v6 sandbox` with local charts:

```bash
v6 sandbox new --local-chart-dir /path/to/vantage6/charts
```

## Release Process

Semver: `Major.Minor.Patch.Pre[N].Post<n>` (e.g. `2.0.1b1`).

```bash
# Create and push release tag (triggers CI pipeline)
git tag version/x.y.z
git push origin version/x.y.z
```

Pipeline: validates tag, updates version in code, builds/pushes Docker images and Helm charts to `ghcr.io/vantage6`, creates GitHub release, publishes to PyPI.

### Testing a release candidate

```bash
uv pip install vantage6==<version> --prerelease=allow

v6 sandbox new \
    --hq-image ghcr.io/vantage6/infrastructure/hq:<version> \
    --ui-image ghcr.io/vantage6/infrastructure/ui:<version> \
    --node-image ghcr.io/vantage6/infrastructure/node:<version> \
    --store-image ghcr.io/vantage6/infrastructure/algorithm-store:<version>
```

## CI Workflows

- **unit_tests.yml**: `make install-dev` + `ruff check` + `coverage run utest.py`
- **code-style.yml**: `ruff check .` + `ruff format --check .`
- **release.yml**: publishes to PyPI via `make publish`
