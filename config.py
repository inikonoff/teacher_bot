import os
from dataclasses import dataclass, field

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    
    # Multiple Groq API keys для rotation
    GROQ_API_KEYS: list = field(default_factory=lambda: os.getenv("GROQ_API_KEYS", "").split(","))
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # Admin IDs для статистики
    ADMIN_IDS: list = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
