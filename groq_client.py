import re
from groq import Groq

class GroqRouter:
    def __init__(self, api_keys: list):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.clients = [Groq(api_key=key) for key in api_keys]
    
    def get_client(self):
        """Rotation API ключей при rate limit"""
        client = self.clients[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.clients)
        return client
    
    def assess_complexity(self, text: str) -> str:
        """
        Быстрая эвристика без LLM вызова
        Simple → llama-3.1-8b-instant (512 tok/s, дешевле по квоте)
        Complex → llama-3.3-70b-versatile (128k context, умнее)
        """
        text_lower = text.lower()
        
        # Простые вопросы (8B модель)
        simple_patterns = [
            r'^как (будет|сказать|написать)',
            r'^что (такое|значит|означает)',
            r'^переведи',
            r'^скажи',
            r'перевод',
            len(text) < 50,
        ]
        
        # Сложные вопросы (70B модель)
        complex_patterns = [
            r'(объясни|explain|разбери|почему)',
            r'(докажи|доказательство|proof)',
            r'(compare|сравни|отличие)',
            r'(анализ|проанализируй)',
            len(text) > 200,
            'формула' in text_lower,
            'теорема' in text_lower,
            'реакция' in text_lower,
            'уравнение' in text_lower,
        ]
        
        # Проверяем сложные паттерны
        for pattern in complex_patterns:
            if isinstance(pattern, bool):
                if pattern:
                    return "llama-3.3-70b-versatile"
            elif re.search(pattern, text_lower):
                return "llama-3.3-70b-versatile"
        
        # Проверяем простые паттерны
        for pattern in simple_patterns:
            if isinstance(pattern, bool):
                if pattern:
                    return "llama-3.1-8b-instant"
            elif re.search(pattern, text_lower):
                return "llama-3.1-8b-instant"
        
        # По умолчанию средняя модель
        return "llama-3.3-70b-versatile"
    
    async def get_response(self, messages: list, max_retries: int = 3):
        """Запрос с fallback на другие API ключи"""
        model = self.assess_complexity(messages[-1]["content"])
        
        for attempt in range(max_retries):
            try:
                client = self.get_client()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                    top_p=0.9
                )
                return response.choices[0].message.content
            
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                    continue
                elif attempt == max_retries - 1:
                    raise Exception(f"Все API ключи исчерпаны: {e}")
        
        return "Извините, сервис временно перегружен. Попробуйте через минуту."
