# Lavalink
Custom Lavalink server for the Collegiate Esports Network

## File Structure
```
plugins/            - plugins folder
application.yml     - lavalink instance config
```

## Architecture
- Lavalink: `v4`
  - Youtube Plugin: `v1.18.0`

## Dependencies
- Always ensure this Lavalink instance remains compatible with `Wavelink v3.5`

## Lavalink Control
**Start Container:**
```bash
docker compose up -d lavalink  # Dev
docker compose -f compose.yaml -f compose.prod.yaml up -d lavalink  # Prod
```

**Stop Container:**
```bash
docker compose stop lavalink
```