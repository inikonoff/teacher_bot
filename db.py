from supabase import create_client, Client
from datetime import datetime, timedelta
from collections import Counter

class Database:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.db: Client = create_client(supabase_url, supabase_key)
    
    async def get_user(self, user_id: int) -> dict | None:
        """Получить пользователя"""
        try:
            result = self.db.table('users') \
                .select('*') \
                .eq('user_id', user_id) \
                .execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"DB get_user error: {e}")
            return None
    
    async def create_user(self, user_id: int, username: str | None):
        """Создать нового пользователя"""
        try:
            self.db.table('users').insert({
                'user_id': user_id,
                'username': username,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print(f"DB create_user error: {e}")
    
    async def update_user_subject(self, user_id: int, subject: str):
        """Обновить выбранный предмет"""
        try:
            self.db.table('users') \
                .update({'current_subject': subject}) \
                .eq('user_id', user_id) \
                .execute()
        except Exception as e:
            print(f"DB update_user_subject error: {e}")
    
    async def log_question(self, user_id: int, subject: str, question: str, from_cache: bool = False):
        """Логировать вопрос для статистики"""
        try:
            self.db.table('questions_log').insert({
                'user_id': user_id,
                'subject': subject,
                'question': question[:500],
                'from_cache': from_cache,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print(f"DB log_question error: {e}")
    
    async def get_stats(self) -> dict:
        """Общая статистика"""
        try:
            total_users = self.db.table('users').select('user_id', count='exact').execute()
            total_questions = self.db.table('questions_log').select('id', count='exact').execute()
            cache_hits = self.db.table('questions_log') \
                .select('id', count='exact') \
                .eq('from_cache', True) \
                .execute()
            
            cache_hit_rate = (cache_hits.count / total_questions.count * 100) if total_questions.count > 0 else 0
            
            return {
                'total_users': total_users.count,
                'total_questions': total_questions.count,
                'cache_hits': cache_hits.count,
                'cache_hit_rate': cache_hit_rate
            }
        except Exception as e:
            print(f"DB get_stats error: {e}")
            return {'total_users': 0, 'total_questions': 0, 'cache_hits': 0, 'cache_hit_rate': 0}
    
    async def get_subject_stats(self) -> list:
        """Статистика по предметам"""
        try:
            result = self.db.table('questions_log').select('subject').execute()
            
            subjects = [row['subject'] for row in result.data if row.get('subject')]
            counter = Counter(subjects)
            
            return [{'subject': subj, 'count': count} for subj, count in counter.most_common()]
        except Exception as e:
            print(f"DB get_subject_stats error: {e}")
            return []
    
    async def get_stats_today(self) -> dict:
        """Статистика за сегодня"""
        try:
            today = datetime.utcnow().date()
            
            new_users = self.db.table('users') \
                .select('user_id', count='exact') \
                .gte('created_at', today.isoformat()) \
                .execute()
            
            questions_today = self.db.table('questions_log') \
                .select('id', count='exact') \
                .gte('created_at', today.isoformat()) \
                .execute()
            
            active_users = self.db.table('questions_log') \
                .select('user_id') \
                .gte('created_at', today.isoformat()) \
                .execute()
            
            unique_active = len(set(row['user_id'] for row in active_users.data))
            
            cache_hits = self.db.table('questions_log') \
                .select('id', count='exact') \
                .eq('from_cache', True) \
                .gte('created_at', today.isoformat()) \
                .execute()
            
            cache_hit_rate = (cache_hits.count / questions_today.count * 100) if questions_today.count > 0 else 0
            
            questions = self.db.table('questions_log') \
                .select('subject') \
                .gte('created_at', today.isoformat()) \
                .execute()
            
            subjects = [row['subject'] for row in questions.data if row.get('subject')]
            top_subjects = [{'subject': s, 'count': c} for s, c in Counter(subjects).most_common(5)]
            
            return {
                'new_users': new_users.count,
                'questions_today': questions_today.count,
                'active_users': unique_active,
                'cache_hit_rate': cache_hit_rate,
                'top_subjects': top_subjects
            }
        except Exception as e:
            print(f"DB get_stats_today error: {e}")
            return {'new_users': 0, 'questions_today': 0, 'active_users': 0, 'cache_hit_rate': 0, 'top_subjects': []}
    
    async def get_stats_week(self) -> dict:
        """Статистика за неделю"""
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            new_users = self.db.table('users') \
                .select('user_id', count='exact') \
                .gte('created_at', week_ago.isoformat()) \
                .execute()
            
            questions_week = self.db.table('questions_log') \
                .select('id', count='exact') \
                .gte('created_at', week_ago.isoformat()) \
                .execute()
            
            active_users = self.db.table('questions_log') \
                .select('user_id') \
                .gte('created_at', week_ago.isoformat()) \
                .execute()
            
            unique_active = len(set(row['user_id'] for row in active_users.data))
            
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
        except Exception as e:
            print(f"DB get_stats_week error: {e}")
            return {'new_users': 0, 'questions_week': 0, 'active_users': 0, 'avg_daily_questions': 0, 'daily_breakdown': []}
    
    async def get_top_users(self, limit: int = 10) -> list:
        """Топ активных пользователей"""
        try:
            questions = self.db.table('questions_log').select('user_id').execute()
            
            user_counts = Counter(row['user_id'] for row in questions.data)
            top_user_ids = [user_id for user_id, _ in user_counts.most_common(limit)]
            
            users = self.db.table('users') \
                .select('user_id', 'username') \
                .in_('user_id', top_user_ids) \
                .execute()
            
            result = []
            for user_id, count in user_counts.most_common(limit):
                user_data = next((u for u in users.data if u['user_id'] == user_id), None)
                result.append({
                    'user_id': user_id,
                    'username': user_data['username'] if user_data else None,
                    'question_count': count
                })
            
            return result
        except Exception as e:
            print(f"DB get_top_users error: {e}")
            return []
    
    async def get_cache_stats(self) -> dict:
        """Статистика кеша"""
        try:
            total = self.db.table('cache').select('key', count='exact').execute()
            
            top_cached = self.db.table('cache') \
                .select('question', 'hit_count', 'subject') \
                .order('hit_count', desc=True) \
                .limit(10) \
                .execute()
            
            all_hits = self.db.table('cache').select('hit_count').execute()
            avg_hits = sum(row['hit_count'] for row in all_hits.data) / len(all_hits.data) if all_hits.data else 0
            
            subjects = [row['subject'] for row in self.db.table('cache').select('subject').execute().data]
            most_cached = Counter(subjects).most_common(1)[0][0] if subjects else "N/A"
            
            return {
                'total_cached': total.count,
                'top_cached': top_cached.data,
                'avg_hits': avg_hits,
                'most_cached_subject': most_cached
            }
        except Exception as e:
            print(f"DB get_cache_stats error: {e}")
            return {'total_cached': 0, 'top_cached': [], 'avg_hits': 0, 'most_cached_subject': 'N/A'}
    
    async def clear_old_cache(self, days: int = 30) -> int:
        """Очистить старый кеш"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            result = self.db.table('cache') \
                .delete() \
                .lt('created_at', cutoff_date) \
                .eq('hit_count', 0) \
                .execute()
            
            return len(result.data) if result.data else 0
        except Exception as e:
            print(f"DB clear_old_cache error: {e}")
            return 0
