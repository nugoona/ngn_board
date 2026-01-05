# BigQuery 테이블 스키마 정리

이 문서는 `winged-precept-443218-v8.ngn_dataset` 데이터셋의 모든 BigQuery 테이블과 컬럼 정보를 정리한 것입니다.

---

## 📋 목차

1. [Cafe24 관련 테이블](#cafe24-관련-테이블)
2. [Meta Ads 관련 테이블](#meta-ads-관련-테이블)
3. [GA4 관련 테이블](#ga4-관련-테이블)
4. [기타 설정/매핑 테이블](#기타-설정매핑-테이블)
5. [집계/요약 테이블](#집계요약-테이블)

---

## Cafe24 관련 테이블

### 1. `cafe24_orders`
주문 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `order_id` | STRING | 주문 ID |
| `order_date` | TIMESTAMP | 주문일시 |
| `payment_date` | TIMESTAMP | 결제일시 |
| `payment_method` | STRING | 결제 방법 |
| `first_order` | BOOLEAN | 첫 주문 여부 |
| `naverpay_payment_information` | STRING | 네이버페이 결제 정보 |
| `paid` | BOOLEAN | 결제 완료 여부 |
| `canceled` | BOOLEAN | 취소 여부 |
| `order_price_amount` | FLOAT | 주문 금액 |
| `shipping_fee` | FLOAT | 배송비 |
| `coupon_discount_price` | FLOAT | 쿠폰 할인 금액 |
| `points_spent_amount` | FLOAT | 사용한 포인트 |
| `credits_spent_amount` | FLOAT | 사용한 크레딧 |
| `membership_discount_amount` | FLOAT | 멤버십 할인 금액 |
| `set_product_discount_amount` | FLOAT | 세트 상품 할인 금액 |
| `app_discount_amount` | FLOAT | 앱 할인 금액 |
| `total_amount_due` | FLOAT | 총 결제 예정 금액 |
| `payment_amount` | FLOAT | 실제 결제 금액 |
| `naverpay_point` | FLOAT | 네이버페이 포인트 |
| `social_name` | STRING | 소셜 네트워크명 |
| `items_sold` | INTEGER | 판매된 상품 개수 |

### 2. `cafe24_order_items_table`
주문 상품 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `order_id` | STRING | 주문 ID |
| `order_item_code` | STRING | 주문 상품 코드 |
| `product_no` | STRING | 상품 번호 |
| `product_name` | STRING | 상품명 |
| `product_price` | FLOAT | 상품 가격 |
| `additional_discount_price` | FLOAT | 추가 할인 금액 |
| `coupon_discount_price` | FLOAT | 쿠폰 할인 금액 |
| `app_item_discount_amount` | FLOAT | 앱 상품 할인 금액 |
| `individual_shipping_fee` | FLOAT | 개별 배송비 |
| `quantity` | INTEGER | 수량 |
| `ordered_date` | TIMESTAMP | 주문일시 |
| `payment_amount` | FLOAT | 결제 금액 |
| `claim_code` | STRING | 클레임 코드 |
| `status_code` | STRING | 상태 코드 (C1, C2, C3: 취소) |

### 3. `cafe24_refunds_table`
환불 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `order_id` | STRING | 주문 ID |
| `order_item_code` | STRING | 주문 상품 코드 |
| `order_date` | DATE | 주문일 |
| `refund_date` | DATE | 환불일 |
| `actual_refund_amount` | FLOAT | 실제 환불 금액 |
| `quantity` | INTEGER | 환불 수량 |
| `used_points` | FLOAT | 사용된 포인트 |
| `used_credits` | FLOAT | 사용된 크레딧 |
| `total_refund_amount` | FLOAT | 총 환불 금액 |
| `refund_code` | STRING | 환불 코드 |

### 4. `daily_cafe24_sales`
일별 Cafe24 판매 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `payment_date` | DATE | 결제일 |
| `mall_id` | STRING | 몰 ID |
| `company_name` | STRING | 회사명 |
| `total_orders` | INTEGER | 총 주문 수 |
| `item_orders` | INTEGER | 상품 주문 수 |
| `item_product_price` | FLOAT | 상품 판매 금액 |
| `total_shipping_fee` | FLOAT | 총 배송비 |
| `total_coupon_discount` | FLOAT | 총 쿠폰 할인 금액 |
| `total_payment` | FLOAT | 총 결제 금액 |
| `total_refund_amount` | FLOAT | 총 환불 금액 |
| `net_sales` | FLOAT | 순매출 (총 결제 - 환불) |
| `total_naverpay_point` | FLOAT | 총 네이버페이 포인트 |
| `total_prepayment` | INTEGER | 선불금 주문 수 |
| `total_first_order` | INTEGER | 첫 주문 수 |
| `total_canceled` | INTEGER | 취소 주문 수 |
| `total_naverpay_payment_info` | INTEGER | 네이버페이 결제 정보 수 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 5. `daily_cafe24_items`
일별 Cafe24 상품별 판매 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `payment_date` | DATE | 결제일 |
| `mall_id` | STRING | 몰 ID |
| `company_name` | STRING | 회사명 |
| `order_id` | STRING | 주문 ID |
| `product_no` | INTEGER | 상품 번호 |
| `product_name` | STRING | 상품명 |
| `product_price` | FLOAT | 상품 가격 |
| `total_quantity` | INTEGER | 총 수량 |
| `total_canceled` | INTEGER | 취소 수량 |
| `item_quantity` | INTEGER | 실제 판매 수량 |
| `item_product_sales` | FLOAT | 상품 판매 금액 |
| `total_first_order` | INTEGER | 첫 주문 수량 |
| `product_url` | STRING | 상품 URL |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 6. `cafe24_products_table`
Cafe24 상품 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `product_no` | STRING | 상품 번호 |
| `category_no` | STRING | 카테고리 번호 |
| `display` | BOOLEAN | 전시 여부 |
| `selling` | BOOLEAN | 판매 여부 |
| `sold_out` | BOOLEAN | 품절 여부 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 7. `cafe24_categories_table`
Cafe24 카테고리 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `category_no` | STRING | 카테고리 번호 |
| `category_name` | STRING | 카테고리명 |
| `parent_category_no` | STRING | 부모 카테고리 번호 |
| `category_depth` | FLOAT | 카테고리 깊이 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

---

## Meta Ads 관련 테이블

### 8. `meta_ads_ad_level`
Meta Ads 광고 레벨 상세 데이터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `ad_id` | STRING | 광고 ID |
| `ad_name` | STRING | 광고명 |
| `adset_id` | STRING | 광고 세트 ID |
| `adset_name` | STRING | 광고 세트명 |
| `campaign_id` | STRING | 캠페인 ID |
| `campaign_name` | STRING | 캠페인명 |
| `account_id` | STRING | 계정 ID |
| `account_name` | STRING | 계정명 |
| `impressions` | INTEGER | 노출 수 |
| `reach` | INTEGER | 도달 수 |
| `clicks` | FLOAT | 클릭 수 |
| `spend` | FLOAT | 광고비 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |
| `shared_purchase_value` | FLOAT | 공유 구매 금액 |
| `ad_status` | STRING | 광고 상태 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 9. `meta_ads_account_summary`
Meta Ads 계정별 일별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `company_name` | STRING | 회사명 |
| `account_id` | STRING | 계정 ID |
| `account_name` | STRING | 계정명 |
| `spend` | FLOAT | 광고비 |
| `impressions` | INTEGER | 노출 수 |
| `clicks` | INTEGER | 클릭 수 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |
| `CPC` | INTEGER | 클릭당 비용 |
| `CTR` | FLOAT | 클릭률 (%) |
| `CPM` | INTEGER | 천회 노출당 비용 |
| `CVR` | FLOAT | 전환률 (%) |
| `ROAS` | FLOAT | 광고 투자 대비 수익률 (%) |
| `CT` | FLOAT | 구매당 비용 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 10. `meta_ads_campaign_summary`
Meta Ads 캠페인별 일별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `company_name` | STRING | 회사명 |
| `account_id` | STRING | 계정 ID |
| `campaign_id` | STRING | 캠페인 ID |
| `campaign_name` | STRING | 캠페인명 |
| `spend` | FLOAT | 광고비 |
| `impressions` | INTEGER | 노출 수 |
| `clicks` | INTEGER | 클릭 수 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |
| `CPC` | INTEGER | 클릭당 비용 |
| `CTR` | FLOAT | 클릭률 (%) |
| `CPM` | INTEGER | 천회 노출당 비용 |
| `CVR` | FLOAT | 전환률 (%) |
| `ROAS` | FLOAT | 광고 투자 대비 수익률 (%) |
| `CT` | FLOAT | 구매당 비용 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 11. `meta_ads_adset_summary`
Meta Ads 광고 세트별 일별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `company_name` | STRING | 회사명 |
| `account_id` | STRING | 계정 ID |
| `campaign_id` | STRING | 캠페인 ID |
| `adset_id` | STRING | 광고 세트 ID |
| `adset_name` | STRING | 광고 세트명 |
| `spend` | FLOAT | 광고비 |
| `impressions` | INTEGER | 노출 수 |
| `clicks` | INTEGER | 클릭 수 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |
| `CPC` | INTEGER | 클릭당 비용 |
| `CTR` | FLOAT | 클릭률 (%) |
| `CPM` | INTEGER | 천회 노출당 비용 |
| `CVR` | FLOAT | 전환률 (%) |
| `ROAS` | FLOAT | 광고 투자 대비 수익률 (%) |
| `CT` | FLOAT | 구매당 비용 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 12. `meta_ads_ad_summary`
Meta Ads 광고별 일별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `company_name` | STRING | 회사명 |
| `account_id` | STRING | 계정 ID |
| `campaign_id` | STRING | 캠페인 ID |
| `adset_id` | STRING | 광고 세트 ID |
| `ad_id` | STRING | 광고 ID |
| `account_name` | STRING | 계정명 |
| `campaign_name` | STRING | 캠페인명 |
| `adset_name` | STRING | 광고 세트명 |
| `ad_name` | STRING | 광고명 |
| `ad_status` | STRING | 광고 상태 |
| `spend` | FLOAT | 광고비 |
| `impressions` | INTEGER | 노출 수 |
| `clicks` | INTEGER | 클릭 수 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |
| `CPC` | INTEGER | 클릭당 비용 |
| `CTR` | FLOAT | 클릭률 (%) |
| `CPM` | INTEGER | 천회 노출당 비용 |
| `CVR` | FLOAT | 전환률 (%) |
| `ROAS` | FLOAT | 광고 투자 대비 수익률 (%) |
| `CT` | FLOAT | 구매당 비용 |
| `updated_at` | TIMESTAMP | 업데이트 일시 |

### 13. `ads_performance`
Meta Ads 성과 데이터 테이블 (레거시)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `account_name` | STRING | 계정명 |
| `spend` | FLOAT | 광고비 |
| `impressions` | INTEGER | 노출 수 |
| `clicks` | INTEGER | 클릭 수 |
| `purchases` | INTEGER | 구매 수 |
| `purchase_value` | FLOAT | 구매 금액 |

### 14. `highest_spend_data`
Meta Ads 최고 광고비 데이터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| (기타 컬럼은 코드에서 확인 필요) | | |

---

## GA4 관련 테이블

### 15. `ga4_traffic`
GA4 트래픽 원본 데이터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `event_date` | DATE | 이벤트 날짜 |
| `ga4_property_id` | INTEGER | GA4 Property ID |
| `first_user_source` | STRING | 첫 방문 소스 |
| `total_users` | INTEGER | 총 사용자 수 |
| `engagement_rate` | FLOAT | 참여율 (%) |
| `bounce_rate` | FLOAT | 이탈률 (%) |
| `event_count` | INTEGER | 이벤트 수 |
| `screen_page_views` | INTEGER | 페이지뷰 수 |

### 16. `ga4_traffic_ngn`
GA4 트래픽 업체별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `event_date` | DATE | 이벤트 날짜 |
| `company_name` | STRING | 회사명 |
| `ga4_property_id` | INTEGER | GA4 Property ID |
| `first_user_source` | STRING | 첫 방문 소스 |
| `total_users` | INTEGER | 총 사용자 수 |
| `engagement_rate` | FLOAT | 참여율 (%) |
| `bounce_rate` | FLOAT | 이탈률 (%) |
| `event_count` | INTEGER | 이벤트 수 |
| `screen_page_views` | INTEGER | 페이지뷰 수 |

### 17. `ga4_viewItem`
GA4 상품 조회 이벤트 원본 데이터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `event_date` | DATE | 이벤트 날짜 |
| `country` | STRING | 국가 |
| `first_user_source` | STRING | 첫 방문 소스 |
| `item_id` | STRING | 상품 ID |
| `view_item` | INTEGER | 상품 조회 수 |
| `ga4_property_id` | INTEGER | GA4 Property ID |

### 18. `ga4_items`
GA4 상품 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `ga4_property_id` | INTEGER | GA4 Property ID |
| `item_id` | STRING | 상품 ID |
| `item_name` | STRING | 상품명 |

### 19. `ga4_viewitem_ngn`
GA4 상품 조회 업체별 집계 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `event_date` | DATE | 이벤트 날짜 |
| `company_name` | STRING | 회사명 |
| `ga4_property_id` | INTEGER | GA4 Property ID |
| `country` | STRING | 국가 |
| `first_user_source` | STRING | 첫 방문 소스 |
| `item_name` | STRING | 상품명 |
| `view_item` | INTEGER | 상품 조회 수 |

---

## 기타 설정/매핑 테이블

### 20. `company_info`
업체 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `company_name` | STRING | 회사명 (소문자) |
| `mall_id` | STRING | 몰 ID |
| `meta_acc` | STRING | 메타 계정명 |
| `main_url` | STRING | 메인 URL |
| `ga4_property_id` | INTEGER | GA4 Property ID (5자리 이상) |
| `meta_business_id` | STRING | 메타 비즈니스 ID |
| `instagram_id` | STRING | Instagram 계정 ID |
| `instagram_acc_name` | STRING | Instagram 계정명 |

### 21. `mall_mapping`
몰 매핑 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `mall_id` | STRING | 몰 ID |
| `company_name` | STRING | 회사명 |
| `main_url` | STRING | 메인 URL |

### 22. `metaAds_acc`
Meta Ads 계정 정보 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `company_name` | STRING | 회사명 |
| `meta_acc_id` | STRING | 메타 광고 계정 ID |
| `meta_acc_name` | STRING | 메타 광고 계정명 |

### 23. `user_accounts`
사용자 계정 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| (스키마는 코드에서 확인 필요) | | |

### 24. `user_company_map`
사용자-회사 매핑 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `user_email` | STRING | 사용자 이메일 |
| `company_name` | STRING | 회사명 |

### 25. `url_product`
URL-상품 매핑 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `company_name` | STRING | 회사명 |
| `product_name` | STRING | 상품명 |
| `product_no` | INTEGER | 상품 번호 |

---

## 집계/요약 테이블

### 26. `performance_summary_ngn`
일별 성과 요약 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| `company_name` | STRING | 회사명 |
| `ad_media` | STRING | 광고 매체 (예: 'meta') |
| `ad_spend` | FLOAT | 광고비 |
| `total_clicks` | INTEGER | 총 클릭 수 |
| `total_purchases` | INTEGER | 총 구매 수 |
| `total_purchase_value` | FLOAT | 총 구매 금액 |
| `roas_percentage` | FLOAT | ROAS (%) |
| `avg_cpc` | FLOAT | 평균 클릭당 비용 |
| `click_through_rate` | FLOAT | 클릭률 (%) |
| `conversion_rate` | FLOAT | 전환률 (%) |
| `site_revenue` | FLOAT | 사이트 매출 |
| `total_visitors` | INTEGER | 총 방문자 수 |
| `product_views` | INTEGER | 상품 조회 수 |
| `views_per_visit` | FLOAT | 방문당 조회 수 |
| `ad_spend_ratio` | FLOAT | 광고비 비율 (%) |
| `avg_order_value` | FLOAT | 평균 주문 금액 |
| `updated_at` | STRING | 업데이트 일시 |

### 27. `sheets_platform_sales_data`
시트 플랫폼 판매 데이터 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `DATE` | DATE | 날짜 (컬럼명이 대문자) |
| (기타 컬럼은 코드에서 확인 필요) | | |

### 28. `instagram_followers`
Instagram 팔로워 수 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `date` | DATE | 날짜 |
| (기타 컬럼은 코드에서 확인 필요) | | |

---

## 📝 참고 사항

### 날짜 컬럼 기준 테이블 정리

다음 테이블들은 날짜 컬럼을 기준으로 데이터 정리 작업이 수행됩니다:

- `cafe24_orders`: `payment_date` (TIMESTAMP)
- `cafe24_order_items_table`: `ordered_date` (TIMESTAMP)
- `daily_cafe24_sales`: `payment_date` (DATE)
- `daily_cafe24_items`: `payment_date` (DATE)
- `cafe24_refunds_table`: `refund_date` (DATE)
- `meta_ads_ad_level`: `date` (DATE)
- `ads_performance`: `date` (DATE)
- `meta_ads_account_summary`: `date` (DATE)
- `meta_ads_adset_summary`: `date` (DATE)
- `meta_ads_campaign_summary`: `date` (DATE)
- `highest_spend_data`: `date` (DATE)
- `ga4_traffic_ngn`: `event_date` (DATE)
- `ga4_viewitem_ngn`: `event_date` (DATE)
- `ga4_traffic`: `event_date` (DATE)
- `ga4_viewItem`: `event_date` (DATE)
- `performance_summary_ngn`: `date` (DATE)
- `sheets_platform_sales_data`: `DATE` (DATE, 컬럼명 대문자)
- `instagram_followers`: `date` (DATE)

### 임시 테이블

다음 테이블들은 작업 중 임시로 생성되는 테이블입니다:

- `temp_orders`
- `temp_order_items_table`
- `temp_cafe24_refunds_table`
- `temp_daily_cafe24_items`
- `temp_cafe24_products_table`
- `temp_cafe24_categories_table`
- `meta_ads_ad_level_temp_{mode}` (mode: today, yesterday 등)
- `performance_summary_temp`

---

**마지막 업데이트**: 2025-01-XX
**데이터셋**: `winged-precept-443218-v8.ngn_dataset`











