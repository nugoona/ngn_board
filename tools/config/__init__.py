"""
자사몰 브랜드 매핑 설정 모듈
"""
from .company_mapping import (
    COMPANY_MAPPING,
    OWN_COMPANY_NAMES,
    get_company_korean_name,
    get_company_brands,
    is_own_company_brand
)

__all__ = [
    'COMPANY_MAPPING',
    'OWN_COMPANY_NAMES',
    'get_company_korean_name',
    'get_company_brands',
    'is_own_company_brand'
]

