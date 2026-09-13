import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "kisan-setu-secure-hackathon-key-2026-agri-tech")
    DATABASE = os.path.join(BASE_DIR, "kisan_setu.db")
    ADMIN_REGISTRATION_KEY = os.environ.get("ADMIN_REGISTRATION_KEY", "KISAN_ADMIN_2026")
    SESSION_COOKIE_NAME = "kisan_setu_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max payload
