Used for:

- MapLibre configuration
- Debugging
- Inspection

---

## 5. Server startup lifecycle

### Phase 1 — Configuration load

- Read source definitions
- Validate required fields
- Fail fast on invalid configuration

---

### Phase 2 — DuckDB initialization (critical)

Performed **once**, synchronously, during server startup:

1. Open DuckDB database (file-backed recommended)
2. Ensure spatial extension is available
3. Load spatial extension **into every connection**
4. Run database sanity checks (see Section 9)

If any step fails → **server must not start**

---

### Phase 3 — Runtime readiness

Only after successful initialization:

- Tile routes are registered
- Requests are accepted

---

## 6. Tile request flow

For `GET /tiles/{source}/{z}/{x}/{y}.pbf`:

1. Validate request (z/x/y bounds, source exists)
2. Enforce `minzoom` / `maxzoom`
3. Cache lookup `(source, z, x, y)`
4. Compute tile envelope using `ST_TileEnvelope(z, x, y)`
5. Spatial filter (`ST_Intersects`)
6. Clip & encode geometry (`ST_AsMVTGeom`)
7. Encode MVT layer (`ST_AsMVT`)
8. Gzip response
9. Store in cache
10. Return response

---

## 7. Concurrency and connections

### Minimal safe model

- Small connection pool (per-request borrow/return)
- Each connection:
  - Loads spatial on creation
  - Is used by one request at a time

**Rule:**  
Every DuckDB connection must explicitly load `spatial`.

**Note:**  
If a pool is used, DuckDB must be file-backed so all connections share the same tables and indexes.

---

## 8. Caching strategy (v0)

### In-process cache

- LRU or size-bounded
- Key: `(source, z, x, y, data_version)`

### HTTP cache

- `Cache-Control: public`
- Long TTL for static datasets

---

## 9. Database sanity checks (explicit & mandatory)

### 9.1 Why sanity checks are required

DuckDB:

- Is embedded
- Has per-connection extension state
- Will silently fail later if spatial is missing

**Therefore:**  
Capabilities must be proven at startup, not discovered at runtime.

---

### 9.2 Sanity check levels

#### Level 1 — Connection liveness
Purpose: ensure DuckDB is running inside the process

- Open a DuckDB connection
- Execute a trivial query

Failure → fatal startup error

---

#### Level 2 — Spatial extension availability
Purpose: ensure spatial exists in the environment

- Verify spatial extension is installed or installable

Failure → fatal startup error  
(usually indicates wrong DuckDB build/version)

---

#### Level 3 — Spatial extension loaded
Purpose: ensure spatial is loaded *in this connection*

- Execute a basic spatial function

Failure → fatal startup error  
(common real-world failure mode)

---

#### Level 4 — Tile helper functions
Purpose: ensure tiling infrastructure exists

- Verify `ST_TileEnvelope` is callable

Failure → fatal startup error

---

#### Level 5 — MVT encoding capability (critical)
Purpose: ensure DuckDB can generate vector tiles

- Verify `ST_AsMVTGeom` exists
- Verify `ST_AsMVT` exists
- Execute a minimal MVT query returning non-NULL binary output

Failure → fatal startup error

---

### 9.3 When checks are executed

| Check Level | When |
|------------|------|
| Levels 1–5 | Server startup |
| Levels 3–5 | Connection pool creation |
| Health check | Runtime |

---

### 9.4 Health endpoint behavior

`/health` reports:

**Healthy**
- All checks pass
- Database reachable
- Spatial + MVT ready

**Unhealthy**
- Any spatial or MVT capability missing
- Connection cannot be opened

Suitable for:
- Manual debugging
- Container readiness checks
- CI/CD smoke tests

---

## 10. Failure philosophy

- Fail fast at startup
- Never retry initialization at request time
- Never install extensions during requests

A broken tile server should:
- Crash loudly
- Restart cleanly
- Never serve partial or invalid tiles

---

## 11. Why this architecture is sane

- Matches DuckDB’s embedded model
- Mirrors PostGIS tile-server validation patterns
- Keeps failure modes deterministic
- Easy to evolve toward:
  - PMTiles generation
  - Multi-source tiles
  - Advanced caching

---

## 12. Next steps (optional)

- Define a source configuration schema
- Compare with Martin’s architecture
- Draft a development plan
- Design a PMTiles export pipeline
