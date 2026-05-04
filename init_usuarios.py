"""
init_usuarios.py — Setea el hash correcto de la contraseña default para todos los usuarios.
Contraseña default: cambiar123
Uso: python init_usuarios.py
"""
import hashlib
import psycopg2

# Leer credenciales desde secrets.toml
try:
    import tomllib
    with open(".streamlit/secrets.toml", "rb") as f:
        s = tomllib.load(f)
    cfg = s["connections"]["postgres"]

    # Si tiene URL directa
    if "url" in cfg:
        from urllib.parse import urlparse, unquote
        parsed   = urlparse(cfg["url"])
        HOST     = parsed.hostname
        PORT     = parsed.port or 5432
        DATABASE = parsed.path.lstrip("/")
        USER     = parsed.username
        PASSWORD = unquote(parsed.password)  # decodifica %XX correctamente
    else:
        HOST     = cfg.get("host", "localhost")
        PORT     = int(cfg.get("port", 5432))
        DATABASE = cfg.get("database", "postgres")
        USER     = cfg.get("username", "postgres")
        PASSWORD = cfg.get("password", "")

except FileNotFoundError:
    # Completar manualmente si no tenés secrets.toml
    HOST     = "aws-1-us-west-2.pooler.supabase.com"
    PORT     = 6543
    DATABASE = "postgres"
    USER     = "postgres.wyoohiislykjhjglbqka"   # ← tu project ref
    PASSWORD = "TU_PASSWORD"                      # ← tu contraseña real

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

DEFAULT_PASS = "cambiar123"
hashed = hash_password(DEFAULT_PASS)

print(f"🔌 Conectando a {HOST}:{PORT}/{DATABASE}...")

try:
    conn = psycopg2.connect(
        host     = HOST,
        port     = PORT,
        dbname   = DATABASE,
        user     = USER,
        password = PASSWORD,
        sslmode  = "require"
    )
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET password_hash = %s", (hashed,))
    conn.commit()
    print(f"✅ Contraseña default seteada para todos los usuarios.")
    print(f"   Contraseña: {DEFAULT_PASS}")
    print(f"   Hash SHA-256: {hashed}")
    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error de conexión: {e}")