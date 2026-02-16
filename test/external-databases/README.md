# External Databases for vantage6 Hub

This directory contains a Docker Compose configuration to run two PostgreSQL databases for testing vantage6 hub with external databases.

## Services

- **hq-db**: PostgreSQL database for vantage6 HQ (server)
  - Port: `5432` (host) → `5432` (container)
  - Database: `vantage6`
  - User: `vantage6`
  - Password: `vantage6`

- **store-db**: PostgreSQL database for vantage6 algorithm store
  - Port: `5433` (host) → `5432` (container)
  - Database: `vantage6_store`
  - User: `vantage6`
  - Password: `vantage6`

## Usage

### Starting the databases

```bash
cd test/external-databases
docker compose up -d
```

### Stopping the databases

```bash
docker compose down
```

To also remove the volumes (this will delete all data):

```bash
docker compose down -v
```

### Checking database status

```bash
docker compose ps
```

## Configuration with `v6 hub new`

When running `v6 hub new`, you will be prompted for database URIs. Use the following:

- **HQ Database URI**: `postgresql://vantage6:vantage6@localhost:5432/vantage6`
- **Algorithm Store Database URI**: `postgresql://vantage6:vantage6@localhost:5433/vantage6_store`

## Important Notes

### Kubernetes Deployment

When deploying the hub to Kubernetes (using `v6 hub start`), the database URIs need to be accessible from within the Kubernetes cluster:

- **For local Kubernetes (e.g., Docker Desktop)**: Replace `localhost` with `host.docker.internal`:
  - HQ: `postgresql://vantage6:vantage6@host.docker.internal:5432/vantage6`
  - Store: `postgresql://vantage6:vantage6@host.docker.internal:5433/vantage6_store`

- **For production**: Use the actual hostname or IP address of the database server that is reachable from your Kubernetes cluster.

### Database Persistence

The databases use Docker volumes (`hq-db-data` and `store-db-data`) to persist data. These volumes will persist even if you stop the containers. To remove them, use `docker compose down -v`.

### Health Checks

Both databases include health checks to ensure they are ready before use. You can check the health status with:

```bash
docker compose ps
```
