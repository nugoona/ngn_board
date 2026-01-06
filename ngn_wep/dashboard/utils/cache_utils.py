"""
Cache utility for BigQuery results and API responses
메모리 기반 캐싱 (SimpleCache) + Redis 선택적 지원
"""
import os
import json
import hashlib
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from functools import wraps

# ============================================================
# 메모리 기반 TTL 캐시 (SimpleCache)
# ============================================================

class SimpleCache:
    """
    TTL을 지원하는 스레드 안전한 인메모리 캐시
    Redis 없이 Flask 프로세스 내에서 동작

    주의사항:
    - Gunicorn 워커 간 캐시 공유 안됨 (각 워커별 독립 캐시)
    - 프로세스 재시작 시 캐시 초기화됨
    - 트래픽이 많아지면 Redis로 전환 권장
    """

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._cleanup_interval = 60  # 60초마다 만료 항목 정리
        self._last_cleanup = time.time()

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (만료 체크 포함)"""
        with self._lock:
            self._maybe_cleanup()

            if key not in self._cache:
                return None

            entry = self._cache[key]
            if entry['expires_at'] and time.time() > entry['expires_at']:
                # 만료됨
                del self._cache[key]
                return None

            return entry['value']

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 값 저장"""
        with self._lock:
            self._maybe_cleanup()

            # 최대 크기 초과 시 가장 오래된 항목 삭제
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_oldest()

            expires_at = time.time() + ttl if ttl else None
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            return True

    def delete(self, key: str) -> bool:
        """캐시에서 키 삭제"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 키 삭제 (간단한 contains 매칭)"""
        with self._lock:
            # 패턴에서 * 제거하고 contains 검색
            search_term = pattern.replace('*', '')
            keys_to_delete = [k for k in self._cache.keys() if search_term in k]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def clear(self):
        """캐시 전체 삭제"""
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        with self._lock:
            valid_count = 0
            expired_count = 0
            now = time.time()

            for entry in self._cache.values():
                if entry['expires_at'] and now > entry['expires_at']:
                    expired_count += 1
                else:
                    valid_count += 1

            return {
                'total_keys': len(self._cache),
                'valid_keys': valid_count,
                'expired_keys': expired_count,
                'max_size': self._max_size
            }

    def _maybe_cleanup(self):
        """주기적으로 만료된 항목 정리"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        keys_to_delete = []

        for key, entry in self._cache.items():
            if entry['expires_at'] and now > entry['expires_at']:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._cache[key]

        if keys_to_delete:
            print(f"[CACHE] 만료된 {len(keys_to_delete)}개 항목 정리됨")

    def _evict_oldest(self):
        """가장 오래된 항목 삭제 (LRU 대신 생성시간 기준)"""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(),
                        key=lambda k: self._cache[k]['created_at'])
        del self._cache[oldest_key]


# ============================================================
# 전역 캐시 인스턴스 및 설정
# ============================================================

# Redis 연결 설정
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Redis 사용 여부 환경변수 체크 (기본값: 비활성화)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"

# 캐시 인스턴스 (지연 초기화)
_simple_cache: Optional[SimpleCache] = None
_redis_client = None
_cache_initialized = False

# 캐시 TTL 설정 (초)
CACHE_TTL = {
    "performance_summary": 300,      # 5분
    "performance_summary_new": 60,   # 1분 (실시간 성능 개선)
    "cafe24_sales": 180,            # 3분
    "cafe24_product_sales": 180,    # 3분
    "viewitem_summary": 600,        # 10분
    "ga4_source_summary": 600,      # 10분
    "product_sales_ratio": 900,     # 15분
    "monthly_net_sales_visitors": 3600,  # 1시간
    "platform_sales": 1800,        # 30분
    "default": 300                  # 5분
}


def _init_cache():
    """
    캐시 초기화 (지연 초기화)
    Redis가 활성화되어 있으면 Redis 사용, 아니면 SimpleCache 사용
    """
    global _simple_cache, _redis_client, _cache_initialized

    if _cache_initialized:
        return

    _cache_initialized = True

    # Redis 활성화된 경우 Redis 연결 시도
    if REDIS_ENABLED:
        try:
            import redis
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=0.5,
                socket_connect_timeout=0.5
            )
            client.ping()  # 연결 테스트
            _redis_client = client
            print(f"[CACHE] Redis 연결 성공: {REDIS_HOST}:{REDIS_PORT}")
            return
        except Exception as e:
            print(f"[CACHE] Redis 연결 실패: {e} - SimpleCache로 폴백")

    # SimpleCache 사용 (기본값)
    _simple_cache = SimpleCache(max_size=500)
    print("[CACHE] SimpleCache(메모리 캐시) 활성화됨")


def _get_cache():
    """현재 사용 중인 캐시 반환"""
    _init_cache()
    return _redis_client if _redis_client else _simple_cache


# ============================================================
# 캐시 유틸리티 함수
# ============================================================

def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    함수명과 파라미터를 기반으로 고유한 캐시 키 생성
    """
    params_str = json.dumps({
        "args": args,
        "kwargs": sorted(kwargs.items())
    }, sort_keys=True, default=str)

    hash_obj = hashlib.sha256(params_str.encode())
    param_hash = hash_obj.hexdigest()[:16]

    return f"ngn_cache:{func_name}:{param_hash}"


def get_cache_ttl(func_name: str) -> int:
    """함수명에 따른 캐시 TTL 반환"""
    return CACHE_TTL.get(func_name, CACHE_TTL["default"])


def cache_get(key: str) -> Optional[Any]:
    """캐시에서 데이터 조회"""
    try:
        cache = _get_cache()
        if cache is None:
            return None

        if isinstance(cache, SimpleCache):
            return cache.get(key)
        else:
            # Redis
            data = cache.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        print(f"[CACHE] 조회 실패: {e}")

    return None


def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """캐시에 데이터 저장"""
    try:
        cache = _get_cache()
        if cache is None:
            return False

        if isinstance(cache, SimpleCache):
            return cache.set(key, value, ttl)
        else:
            # Redis
            data = json.dumps(value, default=str)
            if ttl:
                cache.setex(key, ttl, data)
            else:
                cache.set(key, data)
            return True
    except Exception as e:
        print(f"[CACHE] 저장 실패: {e}")
        return False


def cache_delete(pattern: str = None) -> int:
    """캐시 삭제 (패턴 매칭 지원)"""
    try:
        cache = _get_cache()
        if cache is None:
            return 0

        if isinstance(cache, SimpleCache):
            if pattern:
                return cache.delete_pattern(pattern)
            return 0
        else:
            # Redis
            if pattern:
                keys = cache.keys(pattern)
                if keys:
                    return cache.delete(*keys)
            return 0
    except Exception as e:
        print(f"[CACHE] 삭제 실패: {e}")
        return 0


# ============================================================
# 캐싱 데코레이터
# ============================================================

def cached_query(func_name: str = None, ttl: int = None):
    """
    함수 결과를 캐싱하는 데코레이터

    Args:
        func_name: 캐시 키에 사용할 함수명 (None이면 실제 함수명 사용)
        ttl: 캐시 TTL (None이면 기본값 사용)

    사용 예:
        @cached_query(func_name="performance_summary_new", ttl=60)
        def get_performance_summary_new(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_func_name = func_name or func.__name__
            cache_key = generate_cache_key(cache_func_name, *args, **kwargs)

            # 캐시에서 조회
            try:
                cached_result = cache_get(cache_key)
                if cached_result is not None:
                    return cached_result
            except Exception as e:
                # 캐시 조회 실패 시 무시하고 함수 실행
                print(f"[CACHE] 조회 중 오류 (무시됨): {e}")

            # 캐시 미스 - 실제 함수 실행
            result = func(*args, **kwargs)

            # 결과를 캐시에 저장
            try:
                cache_ttl = ttl or get_cache_ttl(cache_func_name)
                cache_set(cache_key, result, cache_ttl)
            except Exception as e:
                # 캐시 저장 실패 시 무시
                print(f"[CACHE] 저장 중 오류 (무시됨): {e}")

            return result
        return wrapper
    return decorator


# ============================================================
# 관리 및 통계 함수
# ============================================================

def invalidate_cache_by_pattern(pattern: str) -> int:
    """패턴에 매칭되는 모든 캐시 무효화"""
    deleted_count = cache_delete(f"ngn_cache:*{pattern}*")
    if deleted_count > 0:
        print(f"[CACHE] 캐시 무효화: {pattern} - {deleted_count}개 키 삭제")
    return deleted_count


def get_cache_stats() -> Dict[str, Any]:
    """캐시 상태 정보 반환"""
    try:
        cache = _get_cache()
        if cache is None:
            return {"enabled": False, "message": "캐시 초기화 안됨"}

        if isinstance(cache, SimpleCache):
            stats = cache.stats()
            return {
                "enabled": True,
                "type": "SimpleCache (메모리)",
                **stats
            }
        else:
            # Redis
            info = cache.info()
            keys_count = len(cache.keys("ngn_cache:*"))
            return {
                "enabled": True,
                "type": "Redis",
                "keys_count": keys_count,
                "memory_used": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime": info.get("uptime_in_seconds", 0)
            }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def clear_all_cache():
    """모든 캐시 삭제"""
    try:
        cache = _get_cache()
        if cache is None:
            return False

        if isinstance(cache, SimpleCache):
            cache.clear()
            print("[CACHE] SimpleCache 전체 삭제됨")
            return True
        else:
            # Redis - ngn_cache: 프리픽스만 삭제
            keys = cache.keys("ngn_cache:*")
            if keys:
                cache.delete(*keys)
            print(f"[CACHE] Redis 캐시 {len(keys)}개 삭제됨")
            return True
    except Exception as e:
        print(f"[CACHE] 전체 삭제 실패: {e}")
        return False


# ============================================================
# 호환성 래퍼 함수 (기존 코드 호환)
# ============================================================

def get_cached_data(key: str, *args, **kwargs) -> Optional[Any]:
    """캐시에서 데이터 조회 (호환 wrapper 함수)"""
    try:
        return cache_get(key)
    except Exception as e:
        print(f"[CACHE] get_cached_data 조회 실패: {type(e).__name__}")
        return None


def set_cached_data(key: str, value: Any, ttl: int = None, *args, **kwargs) -> bool:
    """캐시에 데이터 저장 (호환 wrapper 함수)"""
    try:
        return cache_set(key, value, ttl)
    except Exception as e:
        print(f"[CACHE] set_cached_data 저장 실패: {type(e).__name__}")
        return False


# 기존 Redis 전용 함수 호환 (deprecated)
def _get_redis_client():
    """
    [Deprecated] Redis 클라이언트 반환
    하위 호환성을 위해 유지. 새 코드에서는 _get_cache() 사용 권장
    """
    _init_cache()
    return _redis_client


# 모듈 로드 시 캐시 상태 출력 (첫 요청 시 초기화됨)
print(f"[CACHE] 모듈 로드됨 - REDIS_ENABLED={REDIS_ENABLED}")
