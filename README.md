# 📋 Sistema de Autorizaciones de Gastos

Aplicación web full-stack construida con **Streamlit + PostgreSQL** para gestionar flujos de autorización de gastos gubernamentales en múltiples niveles.

---

## 🗂️ Estructura del proyecto

```
sistema_autorizaciones/
├── app.py                          # Entry point: login + navegación
├── pages/
│   ├── 01_carga_formulario.py      # Carga de solicitudes de gasto
│   ├── 02_dashboard.py             # Dashboard con métricas y gráficos
│   ├── 03_autorizante1.py          # Autorización nivel 1
│   └── 04_autorizante2.py          # Autorización nivel 2 (final)
├── utils.py                        # Helpers: BD, permisos, formato
├── init_db.py                      # Script de creación de tabla + seed
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .streamlit/
    └── secrets.toml.example        # Plantilla de credenciales
```

---

## 🔐 Usuarios y perfiles

| Perfil | Email | Contraseña | Acceso |
|--------|-------|------------|--------|
| 1 — Admin | `admin@ejemplo.com` | `admin123` | Todo |
| 2 — Autorizante 1 | `auth1@ejemplo.com` | `pass123` | Dashboard, Formulario, Aut.1 |
| 3 — Autorizante 2 | `auth2@ejemplo.com` | `pass123` | Dashboard, Formulario |
| 4 — Usuario | `user@ejemplo.com` | `pass123` | Dashboard, Formulario |
| 5 — Solicitante | `solicitante@ejemplo.com` | `pass123` | Solo Formulario |

---

## ⚙️ Instalación local (sin Docker)

### 1. Prerrequisitos
- Python 3.10+
- PostgreSQL 14+

### 2. Clonar y crear entorno virtual
```bash
git clone <tu-repo>
cd sistema_autorizaciones
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 3. Configurar credenciales
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
Edita `.streamlit/secrets.toml` con tus credenciales reales de PostgreSQL:
```toml
[connections.postgres]
dialect  = "postgresql"
host     = "localhost"
port     = 5432
database = "autorizaciones"
username = "postgres"
password = "tu_password"
```

### 4. Crear la base de datos PostgreSQL
```bash
# Conectar a PostgreSQL y crear la base de datos
psql -U postgres -c "CREATE DATABASE autorizaciones;"
```

### 5. Inicializar la tabla
```bash
# Solo crear tabla
python init_db.py

# Crear tabla + datos de prueba (recomendado para testear)
python init_db.py --seed

# Recrear desde cero
python init_db.py --drop-first --seed
```

### 6. Ejecutar la aplicación
```bash
streamlit run app.py
```
Abre [http://localhost:8501](http://localhost:8501) en tu navegador.

---

## 🐳 Instalación con Docker Compose (recomendado)

```bash
# Levanta PostgreSQL + Streamlit en un solo comando
docker compose up --build

# En segundo plano
docker compose up --build -d

# Ver logs
docker compose logs -f app

# Detener
docker compose down
```

La app estará disponible en [http://localhost:8501](http://localhost:8501).

> **Nota:** El contenedor `app` corre `init_db.py --seed` automáticamente al iniciar.

---

## 📊 Funcionalidades por página

### 📝 Carga Formulario (`/01_carga_formulario`)
- Formulario validado con todos los campos del schema
- Cálculo automático del total (precio × cantidad)
- Preview del total antes de enviar
- Mensajes de éxito/error con `st.balloons()`

### 📊 Dashboard (`/02_dashboard`)
- **KPIs**: total registros, monto total, aprobados nivel 1 y 2, % aprobación final
- **Filtros**: por área, prioridad, estado de autorizaciones, rango de fechas
- **Gráficos Plotly**:
  - 🥧 Pie: distribución por tipo de gasto
  - 📊 Bar: total monetario por prioridad
  - 📈 Área: evolución diaria (últimos 30 días)
  - 📦 Bar apilado: estado de autorizaciones por área
- Tabla completa con export a CSV

### ✅ Autorizante 1 (`/03_autorizante1`)
- Lista solo los formularios **pendientes** (autorizado1 = false/null)
- Cards expandibles con detalle completo de cada solicitud
- Botones **Autorizar / Rechazar** con confirmación en 2 pasos
- Actualiza `autorizado1` + `fecha_aut1 = NOW()`
- Historial de acciones recientes

### 🔐 Autorizante 2 (`/04_autorizante2`)
- Lista formularios con **autorizado1 = true** y autorizado2 pendiente
- Misma UX que Autorizante 1
- Actualiza `autorizado2` + `fecha_aut2 = NOW()`
- Muestra monto total ya aprobado definitivamente

---

## 🗄️ Schema de la base de datos

```sql
CREATE TABLE formularios (
    id               SERIAL PRIMARY KEY,
    solicitante      VARCHAR(255)  NOT NULL,
    area             VARCHAR(255)  NOT NULL,
    bien_servicio    VARCHAR(255)  NOT NULL,
    unidad_medida    VARCHAR(50)   NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL CHECK (precio_unitario > 0),
    cantidad         INTEGER       NOT NULL CHECK (cantidad > 0),
    total            DECIMAL(10,2) GENERATED ALWAYS AS (precio_unitario * cantidad) STORED,
    justificacion    TEXT          NOT NULL,
    tipo_gasto       VARCHAR(100)  NOT NULL,  -- 'Esencial' | 'Serv. Basico' | 'Politica del gobernador'
    prioridad        VARCHAR(20)   NOT NULL,  -- 'Alta' | 'Media' | 'Baja'
    gasto_escuelas   BOOLEAN       DEFAULT FALSE,
    autorizado1      BOOLEAN       DEFAULT FALSE,
    fecha_aut1       TIMESTAMP,
    autorizado2      BOOLEAN       DEFAULT FALSE,
    fecha_aut2       TIMESTAMP,
    created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Variables de entorno (alternativa a secrets.toml)

Si usas Docker o no quieres usar secrets.toml:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=autorizaciones
export DB_USER=postgres
export DB_PASS=mi_password
```

---

## 🚀 Deploy en Streamlit Cloud

1. Sube el repositorio a GitHub.
2. En [share.streamlit.io](https://share.streamlit.io), conecta el repo y elige `app.py`.
3. En **Settings → Secrets**, pega el contenido de tu `secrets.toml`.
4. Necesitarás una base de datos PostgreSQL accesible desde internet (ej: Supabase, Neon, Railway).

---

## 🧪 Testing rápido

```bash
# 1. Inicia la app con datos de prueba
python init_db.py --drop-first --seed
streamlit run app.py

# 2. Login como admin (ve todo)
#    Email: admin@ejemplo.com / Password: admin123

# 3. Login como solicitante (solo formulario)
#    Email: solicitante@ejemplo.com / Password: pass123

# 4. Prueba el flujo completo:
#    Solicitante carga → Auth1 autoriza → Admin aprueba final
```

---

## 📦 Dependencias principales

| Paquete | Versión | Uso |
|---------|---------|-----|
| streamlit | ≥1.35 | Framework web |
| psycopg2-binary | ≥2.9.9 | Driver PostgreSQL |
| plotly | ≥5.20 | Gráficos interactivos |
| pandas | ≥2.2 | Manipulación de datos |
| SQLAlchemy | ≥2.0 | ORM / conexión st.connection |

---

## 📄 Licencia

MIT — libre para uso gubernamental y privado.
