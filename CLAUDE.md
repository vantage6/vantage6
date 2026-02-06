# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vantage6 is a Privacy Enhancing Technology (PET) Operations platform for managing and deploying federated learning (FL) and multi-party computation (MPC) infrastructure. It's a Python monorepo with 8 PyPI packages plus an Angular frontend.

## Desired Behaviour

- Try to make the minimal possible change to fix the solution. For example, do not overengineer or add tests without being asked to
- Never add comments that explain what the code block below does. Only add comments if it is necessary to explain why something is done

## Common Commands

### Installation

```bash
make install-dev    # Editable install of all packages with dev dependencies
make install        # Regular install of all packages
make uninstall      # Uninstall all vantage6 packages
```

### Testing

```bash
# Run all tests with coverage (from repo root)
python utest.py

# Or via make
make test

# Run tests for a specific package
cd vantage6-server && make test
cd vantage6-algorithm-store && make test
```

### Linting/Formatting

```bash
# Python: Black formatter (configured in .pre-commit-config.yaml)
black .

# Pre-commit hooks
pre-commit run --all-files
```

### Building Docker Images

```bash
make image                    # Build node/server image
make algorithm-store-image    # Build algorithm store image
make ui-image                 # Build UI image
make base-image               # Build infrastructure base image
```

### Documentation

```bash
make devdocs    # Run sphinx-autobuild documentation server
```

### UI Development

```bash
cd vantage6-ui
npm install
npm start       # Dev server
npm test        # Run Karma tests
npm run lint    # ESLint
npm run format  # Prettier
```

### Demo Network (for local testing)

```bash
v6 dev create-demo-network    # Create local test setup
v6 dev start-demo-network     # Start server and 2 nodes
v6 node attach                # View node logs
v6 server attach              # View server logs
```

## Architecture

### Package Structure

The monorepo contains 8 Python packages that must be installed in dependency order:

1. **vantage6-common** - Shared utilities (encryption, configuration, serialization, logging)
2. **vantage6-client** - Python client for server API interaction
3. **vantage6-algorithm-tools** - SDK for algorithm development
4. **vantage6** - CLI (`v6` command) for managing nodes and servers
5. **vantage6-node** - Node application (runs algorithms in containers)
6. **vantage6-backend-common** - Shared backend code (server + algorithm store)
7. **vantage6-server** - Central server (Flask REST API, SQLAlchemy ORM)
8. **vantage6-algorithm-store** - Algorithm marketplace

Plus:

- **vantage6-ui** - Angular 19 web application

### Server Architecture (vantage6-server)

```
vantage6-server/vantage6/server/
├── model/           # SQLAlchemy database models
├── resource/        # Flask REST API endpoints
│   ├── common/      # Shared schemas (e.g., tes_schema.py)
│   ├── task.py      # Task management endpoints
│   └── tes.py       # GA4GH TES API compatibility
├── service/         # Business logic layer
├── controller/      # Controllers
├── permission.py    # RBAC authorization
└── db.py            # Database initialization
```

### Test Locations

- `vantage6-common/tests/` - Common utilities tests
- `vantage6-server/tests_server/` - Server tests
- `vantage6-algorithm-store/tests_store/` - Algorithm store tests
- `vantage6/tests_cli/` - CLI tests
- `vantage6-algorithm-tools/tests/algorithm/` - Algorithm tools tests

### Docker Registry

Images are published to `harbor2.vantage6.ai/infrastructure/`:

- `node:VERSION`, `server:VERSION` - Node and server apps
- `ui:VERSION` - Angular UI
- `algorithm-store:VERSION` - Algorithm store
- `algorithm-base:MAJOR.MINOR` - Base image for algorithms

## Key Technologies

- **Python 3.10+** with Flask 3.1, SQLAlchemy 1.4, Gevent, Docker SDK
- **Angular 19** with Material Design, Socket.io, i18n
- **Black** for Python formatting (pre-commit hook)
- **ESLint/Prettier** for TypeScript/Angular

## Credentials for Demo Network

- Username: `dev_admin`
- Password: `password`
- Server URL: `http://127.0.0.1:7601/api`
