import os
from dataclasses import dataclass, field

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    
    # Multiple Groq API keys для rotation
    GROQ_API_KEYS: list = field(default_factory=lambda: [
        key.strip() for key in os.getenv("GROQ_API_KEYS", "").split(",") if key.strip()
    ])
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # Admin IDs для статистики
    ADMIN_IDS: list = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") 
        if x.strip() and x.strip().isdigit()
    ])
    
    def __post_init__(self):
        """Проверка после инициализации"""
        if not self.ADMIN_IDS:
            print(f"[WARNING] ADMIN_IDS пуст! Проверьте .env файл.")
            print(f"[DEBUG] ADMIN_IDS из env: '{os.getenv('ADMIN_IDS', 'НЕ НАЙДЕНО')}'")
        else:
            print(f"[INFO] Admin IDs loaded: {self.ADMIN_IDS}")