# HidroPluvial Web - Especificación Técnica

## Resumen

Webapp que reproduce la experiencia CLI de HidroPluvial en el navegador, con sistema de usuarios y proyectos multi-tenant.

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                        (React + TypeScript)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │    Login     │  │  Dashboard   │  │      Terminal View       │   │
│  │              │  │              │  │  ┌────────────────────┐  │   │
│  │ - Google     │  │ - Proyectos  │  │  │     xterm.js       │  │   │
│  │ - GitHub     │  │ - Cuencas    │  │  │                    │  │   │
│  │ - Email/Pass │  │ - Historial  │  │  │  $ hp wizard       │  │   │
│  │              │  │              │  │  │  > Crear proyecto  │  │   │
│  └──────────────┘  └──────────────┘  │  │  > ...             │  │   │
│                                       │  └────────────────────┘  │   │
│                                       └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  WebSocket (terminal) │
                    │  REST API (auth/data) │
                    └───────────┬───────────┘
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                    │
│                     (FastAPI + Python 3.11)                          │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      API Layer                               │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │    │
│  │  │ /api/auth  │  │ /api/users │  │ /api/projects          │ │    │
│  │  │            │  │            │  │ /api/basins            │ │    │
│  │  │ - login    │  │ - profile  │  │ /api/exports           │ │    │
│  │  │ - register │  │ - settings │  │                        │ │    │
│  │  │ - oauth    │  │            │  │                        │ │    │
│  │  └────────────┘  └────────────┘  └────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  WebSocket Terminal Manager                  │    │
│  │                                                              │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │              Session Manager                         │    │    │
│  │  │                                                      │    │    │
│  │  │  session_abc123 → PTY(hp wizard) → user_1           │    │    │
│  │  │  session_def456 → PTY(hp wizard) → user_2           │    │    │
│  │  │  session_ghi789 → PTY(hp wizard) → user_3           │    │    │
│  │  │                                                      │    │    │
│  │  │  - Timeout: 10 min inactividad                      │    │    │
│  │  │  - Max por usuario: 2 sesiones                      │    │    │
│  │  │  - Max global: configurable (50-200)                │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Process Manager                           │    │
│  │                                                              │    │
│  │  - Spawn PTY con proceso `hp wizard`                        │    │
│  │  - Inyectar variables de entorno (USER_ID, DB_PATH)         │    │
│  │  - Monitorear uso de memoria/CPU                            │    │
│  │  - Kill procesos zombie                                      │    │
│  │  - Graceful shutdown en deploy                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                          DATABASE                                    │
│                         (PostgreSQL)                                 │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   users     │  │  projects   │  │   basins    │                  │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤                  │
│  │ id (uuid)   │  │ id (uuid)   │  │ id (uuid)   │                  │
│  │ email       │  │ user_id  ←──┼──│ project_id  │                  │
│  │ name        │  │ name        │  │ name        │                  │
│  │ avatar_url  │  │ created_at  │  │ area_ha     │                  │
│  │ provider    │  │ updated_at  │  │ slope_pct   │                  │
│  │ created_at  │  │             │  │ ...         │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ tc_results  │  │  analyses   │  │  sessions   │                  │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤                  │
│  │ id          │  │ id          │  │ id          │                  │
│  │ basin_id    │  │ basin_id    │  │ user_id     │                  │
│  │ method      │  │ tc_id       │  │ token       │                  │
│  │ tc_hr       │  │ storm_data  │  │ created_at  │                  │
│  │ parameters  │  │ hydro_data  │  │ expires_at  │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                        FILE STORAGE                                  │
│                    (Local / S3 / MinIO)                              │
│                                                                      │
│  /storage/                                                           │
│    └── users/                                                        │
│        └── {user_id}/                                                │
│            └── exports/                                              │
│                ├── {project_id}_{basin_id}/                          │
│                │   ├── latex/                                        │
│                │   │   ├── report.tex                                │
│                │   │   ├── hidrogramas/                              │
│                │   │   └── hietogramas/                              │
│                │   └── excel/                                        │
│                │       └── analisis.xlsx                             │
│                └── ...                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Stack Tecnológico

### Backend
- **Framework**: FastAPI 0.100+
- **WebSocket**: FastAPI WebSockets + python-socketio
- **PTY**: ptyprocess (Linux/Mac) / winpty (Windows)
- **Auth**: python-jose (JWT) + authlib (OAuth)
- **ORM**: SQLAlchemy 2.0 + alembic (migraciones)
- **Validación**: Pydantic v2
- **Task Queue**: Celery + Redis (para exports pesados)

### Frontend
- **Framework**: React 18 + TypeScript
- **Terminal**: xterm.js + xterm-addon-fit + xterm-addon-web-links
- **UI**: Tailwind CSS + shadcn/ui
- **State**: Zustand o React Query
- **Router**: React Router v6
- **Auth**: OAuth PKCE flow

### Infraestructura
- **Database**: PostgreSQL 15+
- **Cache/Queue**: Redis
- **Storage**: S3-compatible (MinIO para dev, AWS S3 para prod)
- **Container**: Docker + docker-compose
- **Deploy**:
  - Opción económica: Railway / Render / Fly.io
  - Opción escalable: AWS ECS / Google Cloud Run

## Modelo de Datos (PostgreSQL)

```sql
-- Usuarios
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULL si usa OAuth
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    auth_provider VARCHAR(50) DEFAULT 'email',  -- 'email', 'google', 'github'
    auth_provider_id VARCHAR(255),  -- ID del proveedor OAuth
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,

    UNIQUE(auth_provider, auth_provider_id)
);

-- Proyectos (multi-tenant)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, name)
);

-- Cuencas
CREATE TABLE basins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    area_ha REAL NOT NULL,
    slope_pct REAL NOT NULL,
    p3_10 REAL NOT NULL,
    c REAL,
    cn INTEGER,
    length_m REAL,
    notes TEXT,
    nrcs_segments JSONB,
    p2_mm REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(project_id, name)
);

-- Resultados Tc
CREATE TABLE tc_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
    method VARCHAR(50) NOT NULL,
    tc_hr REAL NOT NULL,
    tc_min REAL NOT NULL,
    parameters JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(basin_id, method)
);

-- Análisis completos
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
    tc_result_id UUID NOT NULL REFERENCES tc_results(id),
    storm_data JSONB NOT NULL,      -- StormResult serializado
    hydrograph_data JSONB NOT NULL, -- HydrographResult serializado
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sesiones de terminal activas
CREATE TABLE terminal_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    process_pid INTEGER,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'idle', 'terminated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    terminated_at TIMESTAMP
);

-- Exports generados
CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    basin_id UUID NOT NULL REFERENCES basins(id) ON DELETE CASCADE,
    export_type VARCHAR(20) NOT NULL,  -- 'latex', 'excel', 'pdf'
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP  -- Para limpieza automática
);

-- Índices
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_basins_project_id ON basins(project_id);
CREATE INDEX idx_tc_results_basin_id ON tc_results(basin_id);
CREATE INDEX idx_analyses_basin_id ON analyses(basin_id);
CREATE INDEX idx_terminal_sessions_user_id ON terminal_sessions(user_id);
CREATE INDEX idx_terminal_sessions_status ON terminal_sessions(status);
CREATE INDEX idx_exports_user_id ON exports(user_id);
```

## Flujo de Autenticación

### 1. Registro/Login con Email
```
┌──────────┐     POST /api/auth/register      ┌──────────┐
│  Client  │ ──────────────────────────────→  │  Server  │
│          │     {email, password, name}      │          │
│          │                                   │          │
│          │  ←────────────────────────────── │          │
│          │     {access_token, refresh_token}│          │
└──────────┘                                   └──────────┘
```

### 2. OAuth (Google/GitHub)
```
┌──────────┐                    ┌──────────┐                    ┌──────────┐
│  Client  │                    │  Server  │                    │  OAuth   │
│          │                    │          │                    │ Provider │
│          │                    │          │                    │          │
│  Click   │ GET /api/auth/     │          │                    │          │
│ "Google" │ google/authorize   │          │                    │          │
│ ─────────┼───────────────────→│          │                    │          │
│          │                    │ Redirect │                    │          │
│          │←───────────────────┼──────────┼───────────────────→│          │
│          │                    │          │                    │          │
│          │                    │          │    User consents   │          │
│          │                    │          │←───────────────────│          │
│          │                    │          │                    │          │
│          │ GET /api/auth/     │          │                    │          │
│          │ google/callback    │          │                    │          │
│          │ ?code=xxx          │          │                    │          │
│ ─────────┼───────────────────→│ Exchange │                    │          │
│          │                    │ code for │                    │          │
│          │                    │ token    │───────────────────→│          │
│          │                    │          │←───────────────────│          │
│          │                    │          │                    │          │
│          │                    │ Create/  │                    │          │
│          │                    │ Update   │                    │          │
│          │                    │ User     │                    │          │
│          │                    │          │                    │          │
│          │←───────────────────┼──────────┤                    │          │
│          │ {access_token,     │          │                    │          │
│          │  refresh_token}    │          │                    │          │
└──────────┘                    └──────────┘                    └──────────┘
```

## Flujo de Terminal WebSocket

### Conexión y Spawn de Proceso

```
┌──────────┐                         ┌──────────┐
│  Client  │                         │  Server  │
│ (xterm)  │                         │          │
│          │  WS /ws/terminal        │          │
│          │  + JWT token            │          │
│ ─────────┼────────────────────────→│          │
│          │                         │ Validate │
│          │                         │ JWT      │
│          │                         │          │
│          │                         │ Check    │
│          │                         │ session  │
│          │                         │ limits   │
│          │                         │          │
│          │                         │ Spawn    │
│          │                         │ PTY with │
│          │                         │ hp wizard│
│          │                         │          │
│          │←────────────────────────┼──────────│
│          │  {"type": "connected",  │          │
│          │   "session_id": "xxx"}  │          │
│          │                         │          │
│  User    │  {"type": "input",      │          │
│  types   │   "data": "1\r"}        │ Forward  │
│ ─────────┼────────────────────────→│ to PTY   │
│          │                         │          │
│          │←────────────────────────│ PTY      │
│          │  {"type": "output",     │ output   │
│          │   "data": "..."}        │          │
└──────────┘                         └──────────┘
```

### Manejo de Sesiones

```python
# backend/terminal/session_manager.py

class TerminalSessionManager:
    """Gestiona sesiones de terminal activas."""

    def __init__(
        self,
        max_sessions_per_user: int = 2,
        max_total_sessions: int = 100,
        idle_timeout_seconds: int = 600,  # 10 minutos
    ):
        self.sessions: Dict[str, TerminalSession] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)
        self.max_per_user = max_sessions_per_user
        self.max_total = max_total_sessions
        self.idle_timeout = idle_timeout_seconds

    async def create_session(self, user_id: str) -> TerminalSession:
        """Crea nueva sesión de terminal para un usuario."""
        # Verificar límites
        if len(self.sessions) >= self.max_total:
            raise SessionLimitError("Servidor al máximo de capacidad")

        user_session_count = len(self.user_sessions[user_id])
        if user_session_count >= self.max_per_user:
            raise SessionLimitError(f"Máximo {self.max_per_user} sesiones por usuario")

        # Crear sesión
        session = TerminalSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=datetime.utcnow(),
        )

        # Spawn proceso con entorno aislado por usuario
        session.process = await self._spawn_process(user_id)

        self.sessions[session.id] = session
        self.user_sessions[user_id].append(session.id)

        return session

    async def _spawn_process(self, user_id: str) -> PtyProcess:
        """Spawns isolated hp wizard process."""
        env = os.environ.copy()
        env.update({
            "HIDROPLUVIAL_USER_ID": user_id,
            "HIDROPLUVIAL_DB_URL": f"postgresql://...?user_id={user_id}",
            "HIDROPLUVIAL_STORAGE_PATH": f"/storage/users/{user_id}",
            "TERM": "xterm-256color",
        })

        return PtyProcess.spawn(
            ["python", "-m", "hidropluvial", "wizard"],
            env=env,
            dimensions=(24, 80),
        )

    async def cleanup_idle_sessions(self):
        """Limpia sesiones inactivas (ejecutar periódicamente)."""
        now = datetime.utcnow()
        to_remove = []

        for session_id, session in self.sessions.items():
            idle_time = (now - session.last_activity).total_seconds()
            if idle_time > self.idle_timeout:
                to_remove.append(session_id)

        for session_id in to_remove:
            await self.terminate_session(session_id, reason="idle_timeout")
```

## Modificaciones al CLI para Multi-tenancy

El CLI actual usa SQLite local. Para la webapp necesitamos:

### 1. Abstracción de Database

```python
# hidropluvial/database/base.py

from abc import ABC, abstractmethod

class DatabaseBackend(ABC):
    """Interfaz abstracta para backends de base de datos."""

    @abstractmethod
    def get_projects(self, user_id: str) -> List[Project]:
        pass

    @abstractmethod
    def create_project(self, user_id: str, name: str) -> Project:
        pass

    # ... otros métodos


class SQLiteBackend(DatabaseBackend):
    """Backend SQLite actual (para CLI local)."""
    pass


class PostgreSQLBackend(DatabaseBackend):
    """Backend PostgreSQL (para webapp)."""
    pass


# Factory
def get_database_backend() -> DatabaseBackend:
    backend_type = os.environ.get("HIDROPLUVIAL_DB_BACKEND", "sqlite")

    if backend_type == "postgresql":
        return PostgreSQLBackend(os.environ["HIDROPLUVIAL_DB_URL"])
    else:
        return SQLiteBackend()
```

### 2. Contexto de Usuario

```python
# hidropluvial/context.py

from contextvars import ContextVar

_current_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

def get_current_user_id() -> Optional[str]:
    return _current_user_id.get()

def set_current_user_id(user_id: str):
    _current_user_id.set(user_id)

# Al iniciar el CLI en modo web:
if os.environ.get("HIDROPLUVIAL_USER_ID"):
    set_current_user_id(os.environ["HIDROPLUVIAL_USER_ID"])
```

## Estructura del Proyecto

```
hidropluvial-web/
├── backend/
│   ├── alembic/                    # Migraciones DB
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Settings (pydantic)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependencias (get_db, get_user)
│   │   │   ├── auth.py             # /api/auth/*
│   │   │   ├── users.py            # /api/users/*
│   │   │   ├── projects.py         # /api/projects/*
│   │   │   ├── basins.py           # /api/basins/*
│   │   │   └── exports.py          # /api/exports/*
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── jwt.py              # JWT utils
│   │   │   ├── oauth.py            # OAuth providers
│   │   │   └── password.py         # Hashing
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py          # SQLAlchemy session
│   │   │   └── models.py           # ORM models
│   │   ├── terminal/
│   │   │   ├── __init__.py
│   │   │   ├── websocket.py        # WS endpoint
│   │   │   ├── session_manager.py  # Gestión sesiones
│   │   │   └── pty_handler.py      # PTY wrapper
│   │   └── tasks/
│   │       ├── __init__.py
│   │       └── exports.py          # Celery tasks
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   └── OAuthButtons.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── ProjectList.tsx
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   └── BasinList.tsx
│   │   │   ├── terminal/
│   │   │   │   ├── Terminal.tsx
│   │   │   │   ├── TerminalHeader.tsx
│   │   │   │   └── useTerminal.ts
│   │   │   └── ui/                 # shadcn components
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── useWebSocket.ts
│   │   ├── lib/
│   │   │   ├── api.ts              # API client
│   │   │   └── auth.ts             # Auth helpers
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Terminal.tsx
│   │   │   └── Settings.tsx
│   │   ├── store/
│   │   │   └── auth.ts             # Zustand store
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

## Docker Compose (Desarrollo)

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: hidropluvial
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: hidropluvial
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://hidropluvial:dev_password@db:5432/hidropluvial
      REDIS_URL: redis://redis:6379
      SECRET_KEY: dev-secret-key-change-in-prod
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
    volumes:
      - ./backend:/app
      - ./hidropluvial:/app/hidropluvial  # Montar paquete principal
      - storage_data:/storage
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000
      VITE_WS_URL: ws://localhost:8000
    command: npm run dev

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://hidropluvial:dev_password@db:5432/hidropluvial
      REDIS_URL: redis://redis:6379
    volumes:
      - ./backend:/app
      - ./hidropluvial:/app/hidropluvial
      - storage_data:/storage
    depends_on:
      - db
      - redis
    command: celery -A app.tasks worker --loglevel=info

volumes:
  postgres_data:
  storage_data:
```

## API Endpoints

### Autenticación
```
POST   /api/auth/register          # Registro con email
POST   /api/auth/login             # Login con email
POST   /api/auth/refresh           # Refresh token
POST   /api/auth/logout            # Logout (invalidar token)
GET    /api/auth/google/authorize  # Iniciar OAuth Google
GET    /api/auth/google/callback   # Callback OAuth Google
GET    /api/auth/github/authorize  # Iniciar OAuth GitHub
GET    /api/auth/github/callback   # Callback OAuth GitHub
```

### Usuarios
```
GET    /api/users/me               # Perfil actual
PATCH  /api/users/me               # Actualizar perfil
DELETE /api/users/me               # Eliminar cuenta
```

### Proyectos (requieren autenticación)
```
GET    /api/projects               # Listar proyectos del usuario
POST   /api/projects               # Crear proyecto
GET    /api/projects/{id}          # Detalle proyecto
PATCH  /api/projects/{id}          # Actualizar proyecto
DELETE /api/projects/{id}          # Eliminar proyecto
```

### Cuencas
```
GET    /api/projects/{id}/basins   # Listar cuencas del proyecto
POST   /api/projects/{id}/basins   # Crear cuenca
GET    /api/basins/{id}            # Detalle cuenca
PATCH  /api/basins/{id}            # Actualizar cuenca
DELETE /api/basins/{id}            # Eliminar cuenca
GET    /api/basins/{id}/analyses   # Listar análisis
```

### Terminal
```
WS     /ws/terminal                # WebSocket para terminal
```

### Exports
```
POST   /api/basins/{id}/export     # Generar export (async)
GET    /api/exports/{id}           # Estado del export
GET    /api/exports/{id}/download  # Descargar archivo
```

## Estimación de Costos (Hosting)

### Opción Económica: Railway / Render
- Backend: ~$7/mes (512MB RAM)
- PostgreSQL: ~$7/mes
- Redis: ~$5/mes
- **Total: ~$20/mes** (soporta ~20-30 usuarios simultáneos)

### Opción Media: DigitalOcean / Fly.io
- Droplet/VM: ~$24/mes (4GB RAM)
- Managed PostgreSQL: ~$15/mes
- Redis: $10/mes
- **Total: ~$50/mes** (soporta ~50-100 usuarios simultáneos)

### Opción Escalable: AWS / GCP
- ECS/Cloud Run: ~$30-50/mes (auto-scaling)
- RDS PostgreSQL: ~$30/mes
- ElastiCache Redis: ~$15/mes
- S3: ~$5/mes
- **Total: ~$80-100/mes** (escala automáticamente)

## Roadmap de Implementación

### Fase 1: MVP (2-3 semanas)
- [ ] Setup proyecto (docker-compose, estructura)
- [ ] Backend: Auth básica (email/password + JWT)
- [ ] Backend: CRUD proyectos/cuencas vía API
- [ ] Backend: WebSocket terminal básico
- [ ] Frontend: Login/Register
- [ ] Frontend: Dashboard con lista de proyectos
- [ ] Frontend: Terminal con xterm.js
- [ ] Adaptar CLI para multi-tenancy

### Fase 2: Producción (1-2 semanas)
- [ ] OAuth (Google, GitHub)
- [ ] Exports async (Celery)
- [ ] Descarga de archivos generados
- [ ] UI polish
- [ ] Deploy a producción
- [ ] Monitoreo básico

### Fase 3: Mejoras (ongoing)
- [ ] Compartir proyectos entre usuarios
- [ ] Historial de sesiones
- [ ] Templates de cuencas
- [ ] API pública
- [ ] Documentación
