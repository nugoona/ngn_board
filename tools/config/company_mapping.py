"""
자사몰 브랜드 매핑 설정 파일

각 자사몰의 영문명, 한글명, 그리고 29CM에서 사용되는 브랜드명 목록을 관리합니다.
"""
from typing import Optional, List, Tuple

# 자사몰 매핑 딕셔너리
# key: BigQuery의 company_name (영문, 소문자)
# value: 한글명과 브랜드명 목록
COMPANY_MAPPING = {
    "piscess": {
        "ko": "파이시스",
        "brands": [
            "파이시스",
            "PISCESS",
            "piscess",
            "Piscess",
        ]  # 29CM 데이터에서 나타날 수 있는 다양한 브랜드명 표기
    }
    # 새로운 자사몰 추가 시 여기에 추가:
    # "other_company": {
    #     "ko": "다른업체",
    #     "brands": ["다른업체", "OTHER", "other"]
    # }
}

# 자사몰 영문명 리스트 (BigQuery의 company_name과 동일)
OWN_COMPANY_NAMES = list(COMPANY_MAPPING.keys())


def get_company_korean_name(company_name_en: str) -> Optional[str]:
    """
    영문 company_name을 한글명으로 변환
    
    Args:
        company_name_en: BigQuery의 company_name (예: "piscess")
    
    Returns:
        한글명 (예: "파이시스"), 매핑이 없으면 None
    """
    company = COMPANY_MAPPING.get(company_name_en.lower())
    return company["ko"] if company else None


def get_company_brands(company_name_en: str) -> List[str]:
    """
    자사몰의 브랜드명 목록 반환
    
    Args:
        company_name_en: BigQuery의 company_name (예: "piscess")
    
    Returns:
        브랜드명 리스트 (예: ["파이시스", "PISCESS", ...])
    """
    company = COMPANY_MAPPING.get(company_name_en.lower())
    return company["brands"] if company else []


def is_own_company_brand(brand_name: str, company_name_en: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    브랜드명이 자사몰 브랜드인지 확인
    
    Args:
        brand_name: 확인할 브랜드명 (29CM 데이터의 Brand_Name)
        company_name_en: 특정 자사몰만 확인할 경우 (None이면 모든 자사몰 확인)
    
    Returns:
        (is_own_company, company_name_en) 튜플
        - is_own_company: 자사몰 브랜드인지 여부
        - company_name_en: 매칭된 자사몰의 영문명 (없으면 None)
    """
    brand_name_normalized = brand_name.strip() if brand_name else ""
    
    if company_name_en:
        # 특정 자사몰만 확인
        brands = get_company_brands(company_name_en)
        if brand_name_normalized in brands:
            return True, company_name_en
    else:
        # 모든 자사몰 확인
        for comp_name, comp_info in COMPANY_MAPPING.items():
            if brand_name_normalized in comp_info["brands"]:
                return True, comp_name
    
    return False, None

