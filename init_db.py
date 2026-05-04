"""
init_db.py — Script de inicialización de la base de datos.
Crea la tabla 'formularios' y (opcionalmente) inserta datos de prueba.

Uso:
    python init_db.py
    python init_db.py --seed        # Con datos de prueba
    python init_db.py --drop-first  # Elimina tabla si existe y la recrea
"""

import sys
import argparse
from datetime import datetime, timedelta
import random

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ─── Leer credenciales desde secrets.toml o variables de entorno ──────────
try:
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
    conn_cfg = secrets["connections"]["postgres"]
    DSN = {
        "host":     conn_cfg.get("host", "localhost"),
        "port":     int(conn_cfg.get("port", 5432)),
        "dbname":   conn_cfg.get("database", "autorizaciones"),
        "user":     conn_cfg.get("username", "postgres"),
        "password": conn_cfg.get("password", ""),
    }
except FileNotFoundError:
    import os
    DSN = {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 5432)),
        "dbname":   os.getenv("DB_NAME", "autorizaciones"),
        "user":     os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASS", ""),
    }

# ─── SQL de creación ───────────────────────────────────────────────────────
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS formularios (
    id               SERIAL PRIMARY KEY,
    solicitante      VARCHAR(255)     NOT NULL,
    area             VARCHAR(255)     NOT NULL,
    bien_servicio    VARCHAR(255)     NOT NULL,
    unidad_medida    VARCHAR(50)      NOT NULL,
    precio_unitario  DECIMAL(10,2)    NOT NULL CHECK (precio_unitario > 0),
    cantidad         INTEGER          NOT NULL CHECK (cantidad > 0),
    total            DECIMAL(10,2)    GENERATED ALWAYS AS (precio_unitario * cantidad) STORED,
    justificacion    TEXT             NOT NULL,
    tipo_gasto       VARCHAR(100)     NOT NULL,
    prioridad        VARCHAR(20)      NOT NULL,
    gasto_escuelas   BOOLEAN          DEFAULT FALSE,
    autorizado1      BOOLEAN          DEFAULT FALSE,
    fecha_aut1       TIMESTAMP,
    autorizado2      BOOLEAN          DEFAULT FALSE,
    fecha_aut2       TIMESTAMP,
    created_at       TIMESTAMP        DEFAULT CURRENT_TIMESTAMP
);
"""

DROP_TABLE = "DROP TABLE IF EXISTS formularios;"

# ─── Datos de semilla ──────────────────────────────────────────────────────
SEED_DATA = [
    ("María González",   "Dirección de Salud",      "Guantes de látex",         "Caja",    4500.00,  20, "Esencial",                  "Alta",  True,  True,  True),
    ("Carlos Pérez",     "Secretaría de Educación",  "Resmas A4",                "Resma",   850.50,   50, "Esencial",                  "Media", True,  True,  True),
    ("Ana Rodríguez",    "Ministerio de Obras",      "Cemento portland",         "Bolsa",   1200.00, 100, "Politica del gobernador",   "Alta",  False, True,  False),
    ("Luis Martínez",    "Dirección de Salud",       "Alcohol en gel 5L",        "Unidad",  3200.00,  15, "Serv. Basico",              "Media", False, False, False),
    ("Paula Fernández",  "Secretaría de Educación",  "Toner impresora HP",       "Unidad",  7500.00,   8, "Esencial",                  "Baja",  True,  False, False),
    ("Roberto Silva",    "Ministerio de Hacienda",   "Sillas ergonómicas",       "Unidad", 18000.00,  10, "Politica del gobernador",   "Media", False, True,  False),
    ("Silvia Torres",    "Dirección Vialidad",       "Señales de tránsito",      "Unidad",  5600.00,  25, "Esencial",                  "Alta",  False, False, False),
    ("Diego López",      "Secretaría de Educación",  "Pizarrones blancos",       "Unidad",  9200.00,   6, "Politica del gobernador",   "Baja",  True,  True,  True),
    ("Claudia Gómez",    "Ministerio de Obras",      "Pintura látex 20L",        "Lata",    2400.00,  30, "Esencial",                  "Media", True,  True,  False),
    ("Fernando Ruiz",    "Dirección de Salud",       "Mascarillas quirúrgicas",  "Caja",    1850.00,  40, "Serv. Basico",              "Alta",  False, False, False),
    ("Natalia Cruz",     "Ministerio de Hacienda",   "Cartuchos tinta color",    "Unidad",  3200.00,  12, "Serv. Basico",              "Baja",  True,  False, False),
    ("Martín Vera",      "Dirección Vialidad",       "Gasoil para maquinaria",   "Litro",    280.00, 500, "Esencial",                  "Alta",  False, True,  False),
]

def seed_data(cursor, offset_days=30):
    """Inserta registros de prueba variando la fecha de creación."""
    base = datetime.now()
    for i, row in enumerate(SEED_DATA):
        (solicitante, area, bien, unidad, precio, cant,
         tipo, prioridad, esc, aut1, aut2) = row

        created = base - timedelta(days=random.randint(0, offset_days))
        f_aut1  = created + timedelta(hours=random.randint(2, 48)) if aut1 else None
        f_aut2  = f_aut1  + timedelta(hours=random.randint(2, 24)) if (aut1 and aut2) else None

        cursor.execute("""
            INSERT INTO formularios
                (solicitante, area, bien_servicio, unidad_medida,
                 precio_unitario, cantidad, justificacion,
                 tipo_gasto, prioridad, gasto_escuelas,
                 autorizado1, fecha_aut1, autorizado2, fecha_aut2, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            solicitante, area, bien, unidad,
            precio, cant,
            f"Justificación de prueba para {bien}. Necesario para operaciones del área.",
            tipo, prioridad, esc,
            aut1, f_aut1, aut2, f_aut2, created,
        ))
    print(f"  ✓ {len(SEED_DATA)} registros de prueba insertados.")


# ─── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Inicializa la BD del Sistema de Autorizaciones")
    parser.add_argument("--seed",       action="store_true", help="Insertar datos de prueba")
    parser.add_argument("--drop-first", action="store_true", help="Eliminar tabla antes de crear")
    args = parser.parse_args()

    print(f"\n🔌 Conectando a {DSN['host']}:{DSN['port']}/{DSN['dbname']} como {DSN['user']}...")
    try:
        conn = psycopg2.connect(**DSN)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
    except Exception as e:
        print(f"\n❌ Error de conexión: {e}")
        print("\nVerifica que PostgreSQL esté en ejecución y las credenciales sean correctas.")
        print("Configura: .streamlit/secrets.toml  o  variables de entorno DB_HOST, DB_PORT, etc.")
        sys.exit(1)

    if args.drop_first:
        print("⚠️  Eliminando tabla existente...")
        cur.execute(DROP_TABLE)
        print("  ✓ Tabla eliminada.")

    print("📦 Creando tabla 'formularios'...")
    cur.execute(CREATE_TABLE)
    print("  ✓ Tabla lista.")

    if args.seed:
        print("🌱 Insertando datos de prueba...")
        seed_data(cur)

    cur.close()
    conn.close()
    print("\n✅ Inicialización completada.\n")


if __name__ == "__main__":
    main()
