# Integrated Security and Persistence Fix

This plan addresses two main areas:
1. **Data Recovery**: Restoring the connection to your original PostgreSQL data volume (`blackshotpos_postgres_data`).
2. **Integrated Security**: Adding NKEY-based authentication as a native feature of the BlackShot POS CLI and Sync Agent.

## User Review Required

> [!IMPORTANT]
> **Data Recovery**: I noticed that Docker Compose created a new volume (`docker_postgres_data`) instead of using your existing one (`blackshotpos_postgres_data`). We will modify the `docker-compose.yml` to use your original volume so you get your data back.

## Proposed Changes

### [Persistence Fix]

#### [MODIFY] [docker-compose.yml](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docker/docker-compose.yml)
- Change the `volumes` section to use the `blackshotpos_postgres_data` volume as an external source.
- This ensures the container connects to your previous data.

---

### [Core Dependencies]

#### [MODIFY] [pyproject.toml](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pyproject.toml)
- Add `nkeys` to the dependencies list.

---

### [Native Security Integration]

#### [MODIFY] [pos_core/cli.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/cli.py)
- Add a new `security` sub-command with the following actions:
  - `generate-keys`: Generates a new NKEY pair if it doesn't exist.
  - `show-id`: Displays the Public ID needed for the Central Core.

#### [MODIFY] [bs_sync/agent.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_sync/agent.py)
- Implement NKEY authentication callback using the `NATS_NKEY_SEED` from environment variables.
- Ensure the agent remains functional (connecting without auth) if no NKEY is provided, for backwards compatibility.

## Verification Plan

### Data Recovery
- Run `docker compose up -d` and verify that the database contains your previous data instead of the seeded data from the new volume.

### Security Integration
- Run `blackshot security generate-keys` and verify it generates a valid key.
- Verify the `sync_agent` logs to see if it correctly attempts to use the NKEY when configured.
