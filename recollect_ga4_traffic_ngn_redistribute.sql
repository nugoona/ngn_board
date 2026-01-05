-- ============================================
-- ga4_traffic_ngn 재분배 (ga4_traffic 기반)
-- 2025-12-26 ~ 현재까지
-- ============================================

MERGE `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn` AS target
USING (
    SELECT 
        t.event_date, 
        c.company_name,
        t.ga4_property_id, 
        t.first_user_source,
        SUM(t.total_users) AS total_users,
        -- engagement_rate와 bounce_rate는 가중평균으로 계산
        SAFE_DIVIDE(
            SUM(t.engagement_rate * t.total_users),
            SUM(t.total_users)
        ) AS engagement_rate,
        SAFE_DIVIDE(
            SUM(t.bounce_rate * t.total_users),
            SUM(t.total_users)
        ) AS bounce_rate,
        SUM(t.event_count) AS event_count,
        SUM(t.screen_page_views) AS screen_page_views
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic` t
    LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c 
        ON t.ga4_property_id = c.ga4_property_id
    WHERE DATE(t.event_date) BETWEEN DATE("2025-12-26") AND CURRENT_DATE()
      AND c.company_name IS NOT NULL
    GROUP BY t.event_date, c.company_name, t.ga4_property_id, t.first_user_source
) AS source
ON target.event_date = source.event_date
   AND target.company_name = source.company_name
   AND target.ga4_property_id = source.ga4_property_id
   AND target.first_user_source = source.first_user_source
WHEN MATCHED THEN
    UPDATE SET 
        target.total_users = source.total_users,
        target.engagement_rate = source.engagement_rate,
        target.bounce_rate = source.bounce_rate,
        target.event_count = source.event_count,
        target.screen_page_views = source.screen_page_views
WHEN NOT MATCHED THEN
    INSERT (
        event_date, company_name, ga4_property_id, first_user_source, 
        total_users, engagement_rate, bounce_rate, event_count, screen_page_views
    )
    VALUES (
        source.event_date, source.company_name, source.ga4_property_id, 
        source.first_user_source, source.total_users, 
        source.engagement_rate, source.bounce_rate, 
        source.event_count, source.screen_page_views
    );



