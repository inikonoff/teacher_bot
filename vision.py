from groq import Groq
import base64
import asyncio

class VisionProcessor:
    def __init__(self, groq_router):
        self.groq = groq_router
    
    async def check_content(self, image_bytes: bytes) -> tuple[bool, str]:
        """
        Проверка изображения на образовательный контент
        Возвращает: (is_educational, message)
        Timeout: 20 секунд
        """
        
        # Базовые проверки
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
            return False, "Изображение слишком большое. Попробуйте сфотографировать ближе."
        
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        client = self.groq.get_client()
        
        try:
            # Добавляем timeout 20 секунд
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """Analyze this image. Respond ONLY with JSON:
{
  "is_educational": true/false,
  "content_type": "homework/textbook/notes/diagram/inappropriate/unclear/other"
}

Educational content includes:
- Textbook pages, homework assignments
- Math problems, exercises, diagrams
- Handwritten notes, formulas
- Educational charts, tables

Non-educational (but respond politely):
- Random photos, memes
- Screenshots of unrelated content
- Blurry/unclear images
- Inappropriate content (handle with care)"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.2,
                    max_tokens=150
                ),
                timeout=20.0
            )
            
            result = response.choices[0].message.content
            import json
            analysis = json.loads(result)
            
            is_educational = analysis.get("is_educational", False)
            content_type = analysis.get("content_type", "unclear")
            
            if not is_educational:
                # Вежливые ответы для разных случаев
                messages = {
                    "inappropriate": "Пожалуйста, отправляйте только учебные материалы. Я помогаю с домашними заданиями.",
                    "unclear": "Изображение нечёткое. Попробуйте сфотографировать ещё раз при хорошем освещении.",
                    "other": "Я вижу это изображение, но не могу найти здесь учебное задание. Отправьте фото страницы учебника или тетради."
                }
                message = messages.get(content_type, "Отправьте, пожалуйста, фото с учебным заданием.")
                return False, message
            
            return True, "OK"
        
        except asyncio.TimeoutError:
            print("Vision check timeout after 20 seconds")
            # При таймауте - пропускаем (benefit of doubt)
            return True, "OK"
            
        except Exception as e:
            # При других ошибках - тоже пропускаем
            print(f"Vision check error: {e}")
            return True, "OK"
    
    async def extract_text(self, image_bytes: bytes) -> str:
        """
        OCR через Groq Vision
        Timeout: 45 секунд
        """
        
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        client = self.groq.get_client()
        
        try:
            # Добавляем timeout 45 секунд (OCR может быть медленнее)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """Распознай и перепиши ВЕСЬ текст с этого изображения.
Сохрани:
- Нумерацию заданий
- Математические формулы и выражения
- Структуру текста
- Условия задач

Если текст на иностранном языке - сохрани его как есть."""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2048
                ),
                timeout=45.0
            )
            
            return response.choices[0].message.content
        
        except asyncio.TimeoutError:
            return "Не удалось распознать текст за 45 секунд. Попробуйте сфотографировать ближе и четче, или разбейте на несколько фото."
        
        except Exception as e:
            return f"Не удалось распознать текст. Попробуйте сфотографировать четче: {e}"