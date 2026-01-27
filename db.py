# db.py - добавить методы

from datetime import datetime, timedelta

async def get_stats_today(self) -> dict:
    """Статистика за сегодня"""
    today = datetime.utcnow().date()
    
    # Новые пользователи
    new_users = self.db.table('users') \
        .select('user_id', count='exact') \
        .gte('created_at', today.isoformat()) \
        .execute()
    
    # Вопросы за сегодня
    questions_today = self.db.table('questions_log') \
        .select('id', count='exact') \
        .gte('created_at', today.isoformat()) \
        .execute()
    
    # Активные пользователи
    active_users = self.db.table('questions_log') \
        .select('user_id') \
        .gte('created_at', today.isoformat()) \
        .execute()
    
    unique_active = len(set(row['user_id'] for row in active_users.data))
    
    # Кеш хиты
    cache_hits = self.db.table('questions_log') \
        .select('id', count='exact') \
        .eq('from_cache', True) \
        .gte('created_at', today.isoformat()) \
        .execute()
    
    cache_hit_rate = (cache_hits.count / questions_today.count * 100) if questions_today.count > 0 else 0
    
    # Топ предметов
    questions = self.db.table('questions_log') \
        .select('subject') \
        .gte('created_at', today.isoformat()) \
        .execute()
    
    from collections import Counter
    subjects = [row['subject'] for row in questions.data if row.get('subject')]
    top_subjects = [{'subject': s, 'count': c} for s, c in Counter(subjects).most_common(5)]
    
    return {
        'new_users': new_users.count,
        'questions_today': questions_today.count,
        'active_users': unique_active,
        'cache_hit_rate': cache_hit_rate,
        'top_subjects': top_subjects
    }

async def get_stats_week(self) -> dict:
    """Статистика за неделю"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Новые пользователи
    new_users = self.db.table('users') \
        .select('user_id', count='exact') \
        .gte('created_at', week_ago.isoformat()) \
        .execute()
    
    # Вопросы за неделю
    questions_week = self.db.table('questions_log') \
        .select('id', count='exact') \
        .gte('created_at', week_ago.isoformat()) \
        .execute()
    
    # Активные пользователи
    active_users = self.db.table('questions_log') \
        .select('user_id') \
        .gte('created_at', week_ago.isoformat()) \
        .execute()
    
    unique_active = len(set(row['user_id'] for row in active_users.data))
    
    # Динамика по дням
    daily_breakdown = []
    for i in range(7):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_questions = self.db.table('questions_log') \
            .select('id', count='exact') \
            .gte('created_at', day.isoformat()) \
            .lt('created_at', (day + timedelta(days=1)).isoformat()) \
            .execute()
        
        daily_breakdown.append({
            'date': day.strftime('%d.%m'),
            'count': day_questions.count
        })
    
    daily_breakdown.reverse()
    avg_daily = questions_week.count / 7
    
    return {
        'new_users': new_users.count,
        'questions_week': questions_week.count,
        'active_users': unique_active,
        'avg_daily_questions': avg_daily,
        'daily_breakdown': daily_breakdown
    }

async def get_top_users(self, limit: int = 10) -> list:
    """Топ активных пользователей"""
    questions = self.db.table('questions_log') \
        .select('user_id') \
        .execute()
    
    from collections import Counter
    user_counts = Counter(row['user_id'] for row in questions.data)
    
    top_user_ids = [user_id for user_id, _ in user_counts.most_common(limit)]
    
    # Получаем данные пользователей
    users = self.db.table('users') \
        .select('user_id', 'username') \
        .in_('user_id', top_user_ids) \
        .execute()
    
    # Объединяем данные
    result = []
    for user_id, count in user_counts.most_common(limit):
        user_data = next((u for u in users.data if u['user_id'] == user_id), None)
        result.append({
            'user_id': user_id,
            'username': user_data['username'] if user_data else None,
            'question_count': count
        })
    
    return result

async def get_cache_stats(self) -> dict:
    """Статистика кеша"""
    total = self.db.table('cache') \
        .select('key', count='exact') \
        .execute()
    
    # Топ по хитам
    top_cached = self.db.table('cache') \
        .select('question', 'hit_count', 'subject') \
        .order('hit_count', desc=True) \
        .limit(10) \
        .execute()
    
    # Средние хиты
    all_hits = self.db.table('cache') \
        .select('hit_count') \
        .execute()
    
    avg_hits = sum(row['hit_count'] for row in all_hits.data) / len(all_hits.data) if all_hits.data else 0
    
    # Самый популярный предмет в кеше
    from collections import Counter
    subjects = [row['subject'] for row in self.db.table('cache').select('subject').execute().data]
    most_cached = Counter(subjects).most_common(1)[0][0] if subjects else "N/A"
    
    return {
        'total_cached': total.count,
        'top_cached': top_cached.data,
        'avg_hits': avg_hits,
        'most_cached_subject': most_cached
    }

async def clear_old_cache(self, days: int = 30) -> int:
    """Очистить старый кеш"""
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    result = self.db.table('cache') \
        .delete() \
        .lt('created_at', cutoff_date) \
        .eq('hit_count', 0) \
        .execute()
    
    return len(result.data) if result.data else 0
