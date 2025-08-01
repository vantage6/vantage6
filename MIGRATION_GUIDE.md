# Migration Guide: setup.py/requirements.txt → uv + pyproject.toml

This guide documents the migration from the old setup.py/requirements.txt approach to the modern uv + pyproject.toml workflow.

## What Changed

### Before (setup.py/requirements.txt)
- Individual setup.py files in each package
- Central requirements.txt with pinned versions
- pip-based dependency management
- Manual version synchronization between packages

### After (uv + pyproject.toml)
- pyproject.toml files in each package
- uv for fast dependency resolution and installation
- Centralized dependency management
- Automatic version synchronization

## Migration Steps Completed

### 1. Root pyproject.toml
- Created root `pyproject.toml` with all dependencies
- Configured build system with hatchling
- Added development dependencies and scripts

### 2. Individual Package pyproject.toml Files
Created pyproject.toml for each package:
- `vantage6/pyproject.toml` - Main CLI package
- `vantage6-server/pyproject.toml` - Server package
- `vantage6-node/pyproject.toml` - Node package
- `vantage6-algorithm-store/pyproject.toml` - Algorithm store
- `vantage6-common/pyproject.toml` - Common utilities
- `vantage6-client/pyproject.toml` - Client library
- `vantage6-algorithm-tools/pyproject.toml` - Algorithm tools
- `vantage6-backend-common/pyproject.toml` - Backend common

### 3. Updated Build System
- Updated Dockerfiles to use uv instead of pip
- Updated Makefile to use uv commands
- Configured hatchling as build backend

## New Commands

### Development Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (includes all local packages)
uv sync --dev

# Or use make:
make install-dev
```

### Production Installation
```bash
# Install all packages
uv sync

# Or use make:
make install
```

### Dependency Management
```bash
# Add a new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade

# Remove dependency
uv remove package-name
```

## Benefits of the New System

1. **Faster Installation**: uv is significantly faster than pip
2. **Better Dependency Resolution**: More reliable dependency resolution
3. **Lock File**: uv.lock ensures reproducible builds
4. **Modern Standards**: Uses pyproject.toml (PEP 518/621)
5. **Simplified Workflow**: Single command for dependency management
6. **Better Error Messages**: Clearer error reporting
7. **Native Commands**: Uses uv's optimized commands instead of pip
8. **Automatic Editable Installs**: Local packages are automatically installed in editable mode

## Files to Remove (After Migration is Complete)

Once the migration is fully tested and working:

```bash
# Remove old setup.py files
rm vantage6/setup.py
rm vantage6-server/setup.py
rm vantage6-node/setup.py
rm vantage6-algorithm-store/setup.py
rm vantage6-common/setup.py
rm vantage6-client/setup.py
rm vantage6-algorithm-tools/setup.py
rm vantage6-backend-common/setup.py

# Remove old requirements.txt files
rm requirements.txt
rm vantage6-server/requirements.txt
rm vantage6-node/requirements.txt
rm vantage6-algorithm-store/requirements.txt
```

## Testing the Migration

1. **Clean Environment**: Start with a fresh virtual environment
2. **Install Dependencies**: Run `uv sync`
3. **Install Packages**: Run `make install-dev`
4. **Run Tests**: Execute the test suite
5. **Test Functionality**: Verify all components work correctly

## Troubleshooting

### Common Issues

1. **Version Conflicts**: Use `uv sync --upgrade` to resolve conflicts
2. **Missing Dependencies**: Check pyproject.toml files for missing dependencies
3. **Build Errors**: Ensure hatchling is properly configured

### Rollback Plan

If issues arise, you can rollback by:
1. Restoring the old setup.py files
2. Restoring requirements.txt
3. Reverting Dockerfile changes
4. Using pip instead of uv

## Next Steps

1. **Test Thoroughly**: Ensure all functionality works with the new system
2. **Update CI/CD**: Update GitHub Actions to use uv
3. **Update Documentation**: Update docs to reflect new commands
4. **Team Training**: Ensure team members understand the new workflow
5. **Remove Old Files**: Once confident, remove setup.py and requirements.txt files

## References

- [uv Documentation](https://docs.astral.sh/uv/)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Hatchling Documentation](https://hatch.pypa.io/latest/) 