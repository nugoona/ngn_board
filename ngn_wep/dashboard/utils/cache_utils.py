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

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    # 연결 테스트
    redis_client.ping()
    CACHE_ENABLED = True
    print(f"[CACHE] Redis 연결 성공: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"[CACHE] Redis 연결 실패: {e} - 캐싱 비활성화")
    redis_client = None
    CACHE_ENABLED = False

# 캐시 TTL 설정 (초)
CACHE_TTL = {
    "performance_summary": 300,      # 5분
    "performance_summary_new": 300,  # 5분
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
    
    # 디버깅을 위한 로그 추가
    print(f"[CACHE] 키 생성 - 함수: {func_name}, 파라미터: {params_str}, 해시: {param_hash}")
    
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
    if not CACHE_ENABLED:
        return None
    
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"[CACHE] 조회 실패: {e}")
    
    return None

def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """
    캐시에 데이터 저장
    """
    if not CACHE_ENABLED:
        return False
    
    try:
        data = json.dumps(value, default=str)
        if ttl:
            redis_client.setex(key, ttl, data)
        else:
            redis_client.set(key, data)
        return True
    except Exception as e:
        print(f"[CACHE] 저장 실패: {e}")
        return False

def cache_delete(pattern: str = None) -> int:
    """
    캐시 삭제 (패턴 매칭 지원)
    """
    if not CACHE_ENABLED:
        return 0
    
    try:
        if pattern:
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
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
            # 캐시 비활성화 상태면 바로 실행
            if not CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # 캐시 키 생성
            cache_func_name = func_name or func.__name__
            cache_key = generate_cache_key(cache_func_name, *args, **kwargs)
            
            # 캐시에서 조회
            cached_result = cache_get(cache_key)
            if cached_result is not None:
                print(f"[CACHE] 캐시 히트: {cache_key}")
                return cached_result
            
            # 캐시 미스 - 실제 함수 실행
            print(f"[CACHE] 캐시 미스: {cache_key}")
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
    if not CACHE_ENABLED:
        return {"enabled": False, "message": "Redis 연결 실패"}
    
    try:
        info = redis_client.info()
        keys_count = len(redis_client.keys("ngn_cache:*"))
        
        return {
            "enabled": True,
            "keys_count": keys_count,
            "memory_used": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime": info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)} 