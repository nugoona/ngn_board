"""
Cache utility for BigQuery results and API responses
Redis-based caching with intelligent TTL management
"""
import os
import json
import hashlib
import redis
from datetime import datetime, timedelta
from typing import Any, Optional, Union, Dict, List
from functools import wraps

# Redis 연결 설정
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# Redis 사용 여부 환경변수 체크 (기본값: 비활성화)
# REDIS_ENABLED=true로 설정해야만 Redis 연결 시도
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"

# Redis 클라이언트 지연 초기화 (모듈 임포트 시 연결 시도하지 않음)
redis_client = None
CACHE_ENABLED = False

def _get_redis_client():
    """
    Redis 클라이언트를 지연 초기화 (lazy initialization)
    첫 사용 시에만 연결 시도하여 모듈 임포트 지연 방지
    """
    global redis_client, CACHE_ENABLED
    
    # 환경변수로 Redis 비활성화된 경우 즉시 리턴 (연결 시도 안 함)
    if not REDIS_ENABLED:
        return None
    
    # 이미 연결 시도했고 실패한 경우 재시도하지 않음
    if redis_client is False:
        return None
    
    # 이미 연결된 경우 재사용
    if redis_client is not None:
        return redis_client
    
    # 첫 연결 시도 (타임아웃 매우 짧게 설정)
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_timeout=0.1,  # 타임아웃 0.1초로 단축 (빠른 실패)
            socket_connect_timeout=0.1  # 연결 타임아웃 0.1초로 단축
        )
        # ping() 호출 제거 (연결 시도만 하고 실제 사용 시 검증)
        redis_client = client
        CACHE_ENABLED = True
        print(f"[CACHE] Redis 클라이언트 생성 완료: {REDIS_HOST}:{REDIS_PORT}")
        return redis_client
    except Exception as e:
        print(f"[CACHE] Redis 연결 실패: {e} - 캐싱 비활성화")
        redis_client = False  # 실패 표시 (재시도 방지)
        CACHE_ENABLED = False
        return None

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

def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    함수명과 파라미터를 기반으로 고유한 캐시 키 생성
    """
    # 파라미터를 정렬된 문자열로 변환
    params_str = json.dumps({
        "args": args,
        "kwargs": sorted(kwargs.items())
    }, sort_keys=True, default=str)
    
    # SHA256 해시로 키 생성
    hash_obj = hashlib.sha256(params_str.encode())
    param_hash = hash_obj.hexdigest()[:16]
    
    # 디버깅 로그 제거 (성능 최적화)
    # print(f"[CACHE] 키 생성 - 함수: {func_name}, 파라미터: {params_str}, 해시: {param_hash}")
    
    return f"ngn_cache:{func_name}:{param_hash}"

def get_cache_ttl(func_name: str) -> int:
    """
    함수명에 따른 캐시 TTL 반환
    """
    return CACHE_TTL.get(func_name, CACHE_TTL["default"])

def cache_get(key: str) -> Optional[Any]:
    """
    캐시에서 데이터 조회
    """
    client = _get_redis_client()
    if not client:
        return None
    
    try:
        data = client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"[CACHE] 조회 실패: {e}")
    
    return None

def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """
    캐시에 데이터 저장
    """
    client = _get_redis_client()
    if not client:
        return False
    
    try:
        data = json.dumps(value, default=str)
        if ttl:
            client.setex(key, ttl, data)
        else:
            client.set(key, data)
        return True
    except Exception as e:
        print(f"[CACHE] 저장 실패: {e}")
        return False

def cache_delete(pattern: str = None) -> int:
    """
    캐시 삭제 (패턴 매칭 지원)
    """
    client = _get_redis_client()
    if not client:
        return 0
    
    try:
        if pattern:
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
        return 0
    except Exception as e:
        print(f"[CACHE] 삭제 실패: {e}")
        return 0

def cached_query(func_name: str = None, ttl: int = None):
    """
    함수 결과를 캐싱하는 데코레이터
    
    Args:
        func_name: 캐시 키에 사용할 함수명 (None이면 실제 함수명 사용)
        ttl: 캐시 TTL (None이면 기본값 사용)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Redis 클라이언트 확인 (지연 초기화)
            client = _get_redis_client()
            if not client:
                # 캐시 비활성화 상태면 바로 실행
                return func(*args, **kwargs)
            
            # 캐시 키 생성
            cache_func_name = func_name or func.__name__
            cache_key = generate_cache_key(cache_func_name, *args, **kwargs)
            
            # 캐시에서 조회
            cached_result = cache_get(cache_key)
            if cached_result is not None:
                # print(f"[CACHE] 캐시 히트: {cache_key}")  # 로그 제거 (성능 최적화)
                return cached_result
            
            # 캐시 미스 - 실제 함수 실행
            # print(f"[CACHE] 캐시 미스: {cache_key}")  # 로그 제거 (성능 최적화)
            result = func(*args, **kwargs)
            
            # 결과를 캐시에 저장
            cache_ttl = ttl or get_cache_ttl(cache_func_name)
            cache_set(cache_key, result, cache_ttl)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_by_pattern(pattern: str):
    """
    패턴에 매칭되는 모든 캐시 무효화
    """
    deleted_count = cache_delete(f"ngn_cache:*{pattern}*")
    if deleted_count > 0:
        print(f"[CACHE] 캐시 무효화: {pattern} - {deleted_count}개 키 삭제")
    return deleted_count

def get_cache_stats() -> Dict[str, Any]:
    """
    캐시 상태 정보 반환
    """
    client = _get_redis_client()
    if not client:
        return {"enabled": False, "message": "Redis 연결 실패"}
    
    try:
        info = client.info()
        keys_count = len(client.keys("ngn_cache:*"))
        
        return {
            "enabled": True,
            "keys_count": keys_count,
            "memory_used": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime": info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}

def get_cached_data(key: str, *args, **kwargs) -> Optional[Any]:
    """
    캐시에서 데이터 조회 (호환 wrapper 함수)
    
    Args:
        key: 캐시 키
        *args, **kwargs: 호환성을 위한 추가 파라미터 (사용하지 않음)
    
    Returns:
        캐시된 데이터 또는 None
    """
    try:
        return cache_get(key)
    except Exception as e:
        # 로그만 남기고 예외는 던지지 않음
        print(f"[CACHE] get_cached_data 조회 실패: {type(e).__name__}")
        return None

def set_cached_data(key: str, value: Any, ttl: int = None, *args, **kwargs) -> bool:
    """
    캐시에 데이터 저장 (호환 wrapper 함수)
    
    Args:
        key: 캐시 키
        value: 저장할 데이터
        ttl: 캐시 TTL (초 단위)
        *args, **kwargs: 호환성을 위한 추가 파라미터 (사용하지 않음)
    
    Returns:
        저장 성공 여부 (bool)
    """
    try:
        return cache_set(key, value, ttl)
    except Exception as e:
        # 로그만 남기고 예외는 던지지 않음
        print(f"[CACHE] set_cached_data 저장 실패: {type(e).__name__}")
        return False 