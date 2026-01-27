from supabase import create_client
import hashlib

class Cache:
    def __init__(self, supabase_url, supabase_key):
        self.db = create_client(supabase_url, supabase_key)
    
    def _hash_query(self, subject: str, question: str) -> str:
        """Хеш для кеша"""
        content = f"{subject}:{question.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get(self, subject: str, question: str) -> str | None:
        """Получить из кеша"""
        cache_key = self._hash_query(subject, question)
        
        try:
            result = self.db.table('cache') \
                .select('response') \
                .eq('key', cache_key) \
                .execute()
            
            if result.data:
                # Обновляем счетчик использования
                self.db.table('cache') \
                    .update({'hit_count': result.data[0].get('hit_count', 0) + 1}) \
                    .eq('key', cache_key) \
                    .execute()
                
                return result.data[0]['response']
        except Exception as e:
            print(f"Cache get error: {e}")
        
        return None
    
    async def set(self, subject: str, question: str, response: str):
        """Сохранить в кеш"""
        cache_key = self._hash_query(subject, question)
        
        try:
            self.db.table('cache').upsert({
                'key': cache_key,
                'subject': subject,
                'question': question[:500],  # обрезаем для экономии
                'response': response,
                'hit_count': 0
            }).execute()
        except Exception as e:
            print(f"Cache set error: {e}")
