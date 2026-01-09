#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
29CM 브랜드 ID 기반 상품 수집 테스트 스크립트
- 기존 keyword 기반에서 brandId 기반으로 변경
- 자사몰/경쟁사 구분하여 데이터 수집
- BigQuery 연결 없이 로컬에서 API 로직 검증용
"""
import json
import time
import random
from typing import List, Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# 29CM API 설정
LISTING_API_URL = "https://display-bff-api.29cm.co.kr/api/v1/listing/items?colorchipVariant=treatment"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.29cm.co.kr",
    "Referer": "https://www.29cm.co.kr/",
}

# 브랜드 ID 설정
OWN_BRAND_ID = 17915  # 자사몰 (파이시스)
COMPETITOR_BRAND_IDS = [1138, 9443, 43189, 10473, 1549, 16507, 11649, 4348, 4349, 16723]


def safe_int(v) -> Optional[int]:
    """안전한 int 변환"""
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def safe_float(v) -> Optional[float]:
    """안전한 float 변환"""
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def post_json(url: str, headers: dict, payload: dict) -> dict:
    """POST JSON 요청"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def build_brand_payload(brand_id: int, page: int = 1, size: int = 50) -> dict:
    """
    브랜드 ID 기반 API payload 생성
    - frontBrandNo를 facets.brandFacetInputs 안에 설정
    - sortType: MOST_SOLD (판매순/베스트순)
    """
    return {
        "pageType": "BRAND_HOME",
        "sortType": "MOST_SOLD",
        "facets": {
            "brandFacetInputs": [
                {"frontBrandNo": brand_id}
            ]
        },
        "pageRequest": {"page": page, "size": size},
    }


def extract_top20(resp: dict, brand_id: int) -> tuple:
    """API 응답에서 TOP 20 상품 추출 및 브랜드명 반환"""
    data = resp.get("data") or {}
    items = data.get("items") or data.get("list") or []
    brand_name = data.get("brandName") or data.get("brand_name")

    result = []

    for rank, it in enumerate(items[:20], start=1):
        # v4 API 응답 구조
        item_info = it.get("itemInfo") or it
        item_url = it.get("itemUrl") or {}

        result.append({
            "rank": rank,
            "item_id": safe_int(it.get("itemId") or it.get("item_id")),
            "brand_name": item_info.get("brandName") or brand_name,
            "product_name": item_info.get("productName") or item_info.get("itemName") or it.get("itemName"),
            "price": safe_int(item_info.get("displayPrice") or item_info.get("price") or it.get("price")),
            "discount_rate": safe_int(item_info.get("saleRate") or item_info.get("discountRate")),
            "like_count": safe_int(item_info.get("likeCount") or it.get("likeCount")),
            "review_count": safe_int(item_info.get("reviewCount") or it.get("reviewCount")),
            "review_score": safe_float(item_info.get("reviewScore") or it.get("reviewScore")),
            "thumbnail_url": item_info.get("thumbnailUrl") or it.get("thumbnailUrl"),
            "item_url": item_url.get("webLink") if isinstance(item_url, dict) else it.get("frontItemUrl"),
        })

    return result, brand_name


def fetch_brand_products(brand_id: int) -> tuple:
    """브랜드 ID로 상품 목록 조회 (POST 방식)

    Returns:
        (products, brand_name): 상품 목록과 브랜드명
    """
    try:
        payload = build_brand_payload(brand_id)
        headers = dict(HEADERS)
        headers["Referer"] = f"https://www.29cm.co.kr/store/brand/{brand_id}"

        resp = post_json(LISTING_API_URL, headers, payload)
        return extract_top20(resp, brand_id)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] API HTTPError {e.code}: {body[:500]}")
        return [], None
    except URLError as e:
        print(f"[ERROR] API URLError: {e}")
        return [], None
    except Exception as e:
        print(f"[ERROR] API 오류: {e}")
        return [], None


def print_brand_results(brand_id: int, products: List[Dict], brand_name: str, is_own_mall: bool):
    """브랜드 검색 결과 출력"""
    if not products:
        print(f"[검색 결과] 브랜드ID: {brand_id} | 결과 없음")
        print("-" * 50)
        return

    # 브랜드명 (API 응답 또는 첫 번째 상품에서)
    if not brand_name and products:
        brand_name = products[0].get("brand_name", "알 수 없음")
    mall_type = "자사몰" if is_own_mall else "경쟁사"

    print(f"[검색 결과] 브랜드ID: {brand_id} | 브랜드명: {brand_name} ({mall_type})")

    for product in products:
        rank = product.get("rank", 0)
        product_name = product.get("product_name", "")
        price = product.get("price")
        review_count = product.get("review_count")

        price_str = f"{price:,}원" if price else ""
        review_str = f"리뷰 {review_count}개" if review_count else ""
        extra = f" | {price_str}" if price_str else ""
        extra += f" | {review_str}" if review_str else ""

        print(f"  {rank}. {product_name}{extra}")

    print("-" * 50)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("29CM 브랜드 ID 기반 상품 수집 테스트")
    print(f"API: {LISTING_API_URL}")
    print("facets.brandFacetInputs[].frontBrandNo 사용")
    print("=" * 60)
    print()

    # 전체 브랜드 ID 리스트 (자사몰 + 경쟁사)
    all_brand_ids = [OWN_BRAND_ID] + COMPETITOR_BRAND_IDS

    collected_data = []

    for brand_id in all_brand_ids:
        is_own_mall = (brand_id == OWN_BRAND_ID)

        print(f"\n[INFO] 브랜드 ID {brand_id} 수집 중...")
        products, brand_name = fetch_brand_products(brand_id)

        # 결과 출력
        print_brand_results(brand_id, products, brand_name, is_own_mall)

        # 수집 데이터 저장 (향후 BigQuery 적재용)
        if products:
            collected_data.append({
                "brand_id": brand_id,
                "brand_name": brand_name or (products[0].get("brand_name") if products else None),
                "is_own_mall": is_own_mall,
                "products": products,
            })

        # API 호출 간격 (과도한 요청 방지)
        time.sleep(random.uniform(0.5, 1.0))

    # 요약 출력
    print()
    print("=" * 60)
    print("수집 완료 요약")
    print("=" * 60)

    own_count = sum(1 for d in collected_data if d["is_own_mall"])
    competitor_count = len(collected_data) - own_count

    print(f"자사몰: {own_count}개 브랜드")
    print(f"경쟁사: {competitor_count}개 브랜드")
    print(f"총 수집 상품: {sum(len(d['products']) for d in collected_data)}개")

    # JSON 형태로 데이터 구조 미리보기 (디버깅용)
    print()
    print("[DEBUG] 첫 번째 브랜드 데이터 구조:")
    if collected_data:
        sample = collected_data[0]
        print(json.dumps({
            "brand_id": sample["brand_id"],
            "brand_name": sample["brand_name"],
            "is_own_mall": sample["is_own_mall"],
            "product_count": len(sample["products"]),
            "first_product": sample["products"][0] if sample["products"] else None,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
