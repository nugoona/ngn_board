# GCP Cloud Shell Project Structure
```text
/home/oscar/ngn_board
├── ~
│   └── .ssh
│       └── config
├── add_cart_signup_columns.sql
├── bigquery_data_cleanup
│   ├── check_tables.py
│   ├── deploy_commands.sh
│   ├── deploy.sh
│   ├── Dockerfile
│   ├── main.py
│   ├── README.md
│   ├── requirements.txt
│   └── test_cleanup.py
├── BIGQUERY_TABLES_SCHEMA.md
├── certs
│   ├── client-cert.pem
│   ├── client-key.pem
│   └── server-ca.pem
├── check_cart_signup_data.sql
├── CHECK_DEPLOYMENT_STATUS.sh
├── check_duplicate_performance_summary.sql
├── check_ga4_api_available_dates.sql
├── check_performance_summary_row_count.sql
├── check_piscess_cart_signup_daily.sql
├── check_piscess_cart_signup_missing_dates.sql
├── check_piscess_cart_signup_monthly_detail.sql
├── check_piscess_cart_signup_monthly.sql
├── check_piscess_data_exists_performance_summary.sql
├── check_piscess_exists_2025_08.sql
├── check_piscess_in_base_tables_2025_08.sql
├── check_piscess_missing_dates_detailed.sql
├── check_piscess_monthly_collection_status.sql
├── check_refund_source_data.sql
├── cleanup_all_daily_sales_errors.sql
├── cleanup_all_duplicate_refunds_fixed.sql
├── cleanup_all_duplicate_refunds.sql
├── cleanup_and_reprocess_daily_sales.sql
├── cleanup_refunds_step_by_step_fixed.sql
├── cleanup_refunds_step_by_step.sql
├── cloudbuild.yaml
├── cloud_function_crawl
│   ├── main.py
│   ├── requirements.txt
│   └── result.html
├── collect_all_performance_summary.sh
├── collect_performance_summary_range.py
├── config
│   ├── google-application-credentials.env
│   ├── mataTokens.json
│   ├── ngn.env
│   ├── .ngn.env.swp
│   └── service-account.json
├── DASHBOARD_AUDIT.md
├──  --date=short  head -20
├── debug_cleaned_table.sql
├── debug_prompts.log
├── delete_and_reprocess_daily_sales.sql
├── deploy_ably_job.sh
├── deploy_all_fixed_jobs.sh
├── deploy_all_refund_sales_jobs.sh
├── deploy_dashboard_safe.sh
├── DEPLOYMENT_TROUBLESHOOTING.md
├── deploy_optimizations.sh
├── deploy_performance_summary_jobs.sh
├── deploy_refund_job.sh
├── deploy_sales_jobs.sh
├── deploy_sheet_platform_job.sh
├── diagnose_refund_issue_2025_12_23.sql
├── diagnosis_refund_query.sql
├── docker
│   ├── Dockerfile-29cm-best
│   ├── Dockerfile-ably-best
│   ├── Dockerfile-catalog
│   ├── Dockerfile-dashboard
│   ├── Dockerfile-dynamic_Ads_meta
│   ├── Dockerfile-fetch_instagram_followers
│   ├── Dockerfile-ga4-traffic
│   ├── Dockerfile-ga4-traffic-yesterday
│   ├── Dockerfile-ga4-view
│   ├── Dockerfile-ga4-view-ngn
│   ├── Dockerfile-ga4-view-yesterday
│   ├── Dockerfile-items-today
│   ├── Dockerfile-items-yesterday
│   ├── Dockerfile-metaAds
│   ├── Dockerfile-MetaAds-today
│   ├── Dockerfile-MetaAds-yesterday
│   ├── Dockerfile-MetaSummary-today
│   ├── Dockerfile-MetaSummary-yesterday
│   ├── Dockerfile-monthly-ai-analysis
│   ├── Dockerfile-monthly-rollup
│   ├── Dockerfile-monthly-snapshot
│   ├── Dockerfile-orders
│   ├── Dockerfile-orders-last_7
│   ├── Dockerfile-orders-yesterday
│   ├── Dockerfile-performance_summary-today
│   ├── Dockerfile-performance_summary-yesterday
│   ├── Dockerfile-product
│   ├── Dockerfile-product-last_7
│   ├── Dockerfile-product-yesterday
│   ├── Dockerfile-refund
│   ├── Dockerfile-sales-today
│   ├── Dockerfile-sales-yesterday
│   ├── Dockerfile-sheet-event-collector
│   ├── Dockerfile-Sheet-update
│   ├── Dockerfile-Sheet-update-yesterday
│   └── token_refresh.Dockerfile
├── .env
├── et --hard HEAD~1
├── fix_cleaned_table.sql
├── FORCE_NEW_DEPLOYMENT.sh
├── gcp_tree.md
├── .gitignore
├── gunicorn.log
├── hboarddockerDockerfile-dashboard
├── home_page
│   ├── about.html
│   ├── app
│   │   ├── app.py
│   │   └── templates
│   │       └── base.html
│   ├── css
│   │   └── style.css
│   ├── images
│   │   ├── favicon.ico
│   │   ├── logo.png
│   │   └── x.png
│   ├── index.html
│   ├── js
│   │   └── main.js
│   ├── portfolio.html
│   ├── requirements.txt
│   ├── services.html
│   ├── technology.html
│   └── videos
│       ├── main2._ngn.mp4
│       └── main._ngn.mp4
├── index.html
├── job-config.yaml
├── jobs
│   └── ngn-orders-job.yaml
├── lh_report.report.html
├── lh_report.report.json
├── logs
├── mobile_backup_20250804_210433.zip
├── MONTHLY_REPORT_NEW_BADGE_COST_OPTIMIZED.md
├── MONTHLY_REPORT_NEW_BADGE_IMPLEMENTATION.md
├── NEW_COMPANY_SETUP_GUIDE.md
├── ngn_wep
│   ├── bandit.txt
│   ├── cafe24_api
│   │   ├── cafe24_refund_data_handler.py
│   │   ├── daily_cafe24_items_handler.py
│   │   ├── daily_cafe24_sales_handler.py
│   │   ├── orders_handler.py
│   │   ├── product_catalog_data_handler.py
│   │   ├── product_handler.py
│   │   ├── token_refresh.py
│   │   └── tokens.json
│   ├── complexity.txt
│   ├── dashboard
│   │   ├── app.py
│   │   ├── bandit.txt
│   │   ├── complexity.txt
│   │   ├── .gitignore
│   │   ├── handlers
│   │   │   ├── accounts_handler.py
│   │   │   ├── auth_handler.py
│   │   │   ├── data_handler.py
│   │   │   ├── __init__.py
│   │   │   └── mobile_handler.py
│   │   ├── __init__.py
│   │   ├── logs
│   │   │   └── flask.log
│   │   ├── requirements.txt
│   │   ├── services
│   │   │   ├── cafe24_service.py
│   │   │   ├── catalog_sidebar_service.py
│   │   │   ├── data_service.py
│   │   │   ├── Fetch_Adset_Summary.py
│   │   │   ├── filter_service.py
│   │   │   ├── ga4_source_summary.py
│   │   │   ├── __init__.py
│   │   │   ├── insert_performance_summary.py
│   │   │   ├── meta_ads_insight.py
│   │   │   ├── meta_ads_preview_backup_20250118_143000.py
│   │   │   ├── meta_ads_preview.py
│   │   │   ├── meta_ads_service.py
│   │   │   ├── meta_ads_slide_collection.py
│   │   │   ├── meta_demo_handler.py
│   │   │   ├── meta_demo_service.py
│   │   │   ├── monthly_net_sales_visitors.py
│   │   │   ├── performance_summary_backup.py
│   │   │   ├── performance_summary_new.py
│   │   │   ├── performance_summary.py
│   │   │   ├── platform_sales_summary.py
│   │   │   ├── product_sales_ratio.py
│   │   │   ├── README.md
│   │   │   ├── test_meta_ads_insight.py
│   │   │   └── viewitem_summary.py
│   │   ├── static
│   │   │   ├── css
│   │   │   │   └── monthly_report.css
│   │   │   ├── demo_ads
│   │   │   │   ├── demo_1.jpg
│   │   │   │   ├── demo_2.jpg
│   │   │   │   ├── demo_3.jpg
│   │   │   │   ├── demo_4.jpg
│   │   │   │   ├── demo_5.jpg
│   │   │   │   ├── demo_6.jpg
│   │   │   │   ├── demo_7.jpg
│   │   │   │   └── demo_8.jpg
│   │   │   ├── img
│   │   │   │   ├── favicon.ico
│   │   │   │   └── x.png
│   │   │   ├── js
│   │   │   │   ├── cafe24_product_sales.js
│   │   │   │   ├── cafe24_sales.js
│   │   │   │   ├── catalog_sidebar.js
│   │   │   │   ├── common.js
│   │   │   │   ├── common_ui.js
│   │   │   │   ├── dashboard_backup_20250118_143500.js
│   │   │   │   ├── dashboard_backup_20250127_emergency.js
│   │   │   │   ├── dashboard.js
│   │   │   │   ├── fetch_data.js
│   │   │   │   ├── filters_backup_20250118_143500.js
│   │   │   │   ├── filters.js
│   │   │   │   ├── ga4_source_summary.js
│   │   │   │   ├── loading_utils.js
│   │   │   │   ├── meta_ads_adset_summary_by_type.js
│   │   │   │   ├── meta_ads_insight_table.js
│   │   │   │   ├── meta_ads.js
│   │   │   │   ├── meta_ads_preview.js
│   │   │   │   ├── meta_ads_slide_collection.js
│   │   │   │   ├── meta_ads_state.js
│   │   │   │   ├── meta_ads_tags.js
│   │   │   │   ├── meta_ads_utils.js
│   │   │   │   ├── meta_demo.js
│   │   │   │   ├── mobile_dashboard_backup_20250729_014304.js
│   │   │   │   ├── mobile_dashboard.js
│   │   │   │   ├── mobile_detection.js
│   │   │   │   ├── monthly_net_sales_visitors.js
│   │   │   │   ├── monthly_report.js
│   │   │   │   ├── pagination.js
│   │   │   │   ├── performance_monitor.js
│   │   │   │   ├── performance_summary.js
│   │   │   │   ├── platform_sales_monthly.js
│   │   │   │   ├── platform_sales_ratio.js
│   │   │   │   ├── platform_sales_summary.js
│   │   │   │   ├── product_sales_ratio.js
│   │   │   │   ├── README.md
│   │   │   │   ├── request_utils.js
│   │   │   │   ├── session_timeout.js
│   │   │   │   └── viewitem_summary.js
│   │   │   ├── mobile_styles.css
│   │   │   ├── pagination.js
│   │   │   ├── sample
│   │   │   ├── styles_backup_20250127_emergency.css
│   │   │   ├── styles_backup.css
│   │   │   ├── styles.css
│   │   │   └── widgets
│   │   ├── templates
│   │   │   ├── ads_page.html
│   │   │   ├── components
│   │   │   │   ├── cafe24_product_sales_table.html
│   │   │   │   ├── cafe24_sales_table.html
│   │   │   │   ├── catalog_sidebar.html
│   │   │   │   ├── filters.html
│   │   │   │   ├── ga4_source_summary_table.html
│   │   │   │   ├── meta_ads_adset_summary_by_type_table.html
│   │   │   │   ├── meta_ads_adset_summary_chart.html
│   │   │   │   ├── meta_ads_insight_table.html
│   │   │   │   ├── meta_ads_preview_cards.html
│   │   │   │   ├── meta_ads_slide_collection_table.html
│   │   │   │   ├── meta_ads_table.html
│   │   │   │   ├── monthly_net_sales_visitors_chart.html
│   │   │   │   ├── monthly_report_modal.html
│   │   │   │   ├── performance_summary_table.html
│   │   │   │   ├── platform_sales_monthly.html
│   │   │   │   ├── platform_sales_ratio.html
│   │   │   │   ├── platform_sales_summary_table.html
│   │   │   │   ├── product_sales_ratio_chart.html
│   │   │   │   ├── product_sales_ratio.html
│   │   │   │   └── viewitem_summary_table.html
│   │   │   ├── delete_info.html
│   │   │   ├── index.html
│   │   │   ├── index_mobile.html
│   │   │   ├── login.html
│   │   │   ├── meta_demo.html
│   │   │   ├── mobile
│   │   │   │   ├── dashboard_backup_20250729_014252.html
│   │   │   │   ├── dashboard_backup_before_design_update.html
│   │   │   │   ├── dashboard_backup_.html
│   │   │   │   ├── dashboard.html
│   │   │   │   └── login.html
│   │   │   ├── privacy.html
│   │   │   ├── README.md
│   │   │   └── terms.html
│   │   ├── templates_backup
│   │   │   ├── ads_page.html
│   │   │   ├── components
│   │   │   │   ├── cafe24_product_sales_table.html
│   │   │   │   ├── cafe24_sales_table.html
│   │   │   │   ├── catalog_sidebar.html
│   │   │   │   ├── filters.html
│   │   │   │   ├── ga4_source_summary_table.html
│   │   │   │   ├── meta_ads_adset_summary_by_type_table.html
│   │   │   │   ├── meta_ads_insight_table.html
│   │   │   │   ├── meta_ads_preview_cards.html
│   │   │   │   ├── meta_ads_slide_collection_table.html
│   │   │   │   ├── meta_ads_table.html
│   │   │   │   ├── monthly_net_sales_visitors_chart.html
│   │   │   │   ├── performance_summary_table.html
│   │   │   │   ├── platform_sales_monthly.html
│   │   │   │   ├── platform_sales_ratio.html
│   │   │   │   ├── platform_sales_summary_table.html
│   │   │   │   ├── product_sales_ratio.html
│   │   │   │   └── viewitem_summary_table.html
│   │   │   ├── delete_info.html
│   │   │   ├── index.html
│   │   │   ├── login.html
│   │   │   ├── meta_demo.html
│   │   │   ├── privacy.html
│   │   │   ├── README.md
│   │   │   └── terms.html
│   │   └── utils
│   │       ├── cache_utils.py
│   │       ├── date_utils.py
│   │       ├── __init__.py
│   │       └── query_utils.py
│   ├── GA4_API
│   │   ├── ga4_cart_signup_test.py
│   │   ├── ga4_traffic_range.py
│   │   ├── ga4_traffic_today.py
│   │   ├── ga4_viewitem_today.py
│   │   └── sheet_update_custom.py
│   ├── __init__.py
│   ├── logs
│   │   └── flask.log
│   ├── meta_api
│   │   ├── adset_config.json
│   │   ├── dynamic_Ads_meta.py
│   │   ├── Merge_Meta_Ads_Summary.py
│   │   └── meta_ads_handler.py
│   ├── period_filter.py
│   ├── queries
│   │   ├── custom_date_range.sql
│   │   ├── daily_query.py
│   │   ├── __init__.py
│   │   ├── period_filter.py
│   │   └── .period_filter.py.swp
│   ├── service-account.json -> /home/oscar/ngn_board/config/service-account.json
│   └── templates_backup
│       ├── ads_page.html
│       ├── components
│       │   ├── cafe24_product_sales_table.html
│       │   ├── cafe24_sales_table.html
│       │   ├── catalog_sidebar.html
│       │   ├── filters.html
│       │   ├── ga4_source_summary_table.html
│       │   ├── meta_ads_adset_summary_by_type_table.html
│       │   ├── meta_ads_insight_table.html
│       │   ├── meta_ads_preview_cards.html
│       │   ├── meta_ads_slide_collection_table.html
│       │   ├── meta_ads_table.html
│       │   ├── monthly_net_sales_visitors_chart.html
│       │   ├── performance_summary_table.html
│       │   ├── platform_sales_monthly.html
│       │   ├── platform_sales_ratio.html
│       │   ├── platform_sales_summary_table.html
│       │   ├── product_sales_ratio.html
│       │   └── viewitem_summary_table.html
│       ├── delete_info.html
│       ├── index.html
│       ├── login.html
│       ├── meta_demo.html
│       ├── privacy.html
│       ├── README.md
│       └── terms.html
├── ngn_wep_backup_20250726_103350
│   ├── cafe24_api
│   │   ├── cafe24_refund_data_handler.py
│   │   ├── daily_cafe24_items_handler.py
│   │   ├── daily_cafe24_sales_handler.py
│   │   ├── orders_handler.py
│   │   ├── product_catalog_data_handler.py
│   │   ├── product_handler.py
│   │   ├── token_refresh.py
│   │   └── tokens.json
│   ├── GA4_API
│   │   ├── ga4_traffic_today.py
│   │   ├── ga4_viewitem_today.py
│   │   └── sheet_update_custom.py
│   ├── __init__.py
│   ├── logs
│   ├── meta_api
│   │   ├── adset_config.json
│   │   ├── dynamic_Ads_meta.py
│   │   ├── Merge_Meta_Ads_Summary.py
│   │   └── meta_ads_handler.py
│   ├── ngn.env -> /home/oscar/ngn_board/ngn.env
│   ├── period_filter.py
│   ├── queries
│   │   ├── custom_date_range.sql
│   │   ├── daily_query.py
│   │   ├── __init__.py
│   │   ├── period_filter.py
│   │   └── .period_filter.py.swp
│   └── service-account.json -> /home/oscar/ngn_board/service-account.json
├── ngn_wep_backup_20250726_103518
│   ├── config
│   │   └── ngn.env
│   ├── ngn_wep
│   │   ├── cafe24_api
│   │   │   ├── cafe24_refund_data_handler.py
│   │   │   ├── daily_cafe24_items_handler.py
│   │   │   ├── daily_cafe24_sales_handler.py
│   │   │   ├── orders_handler.py
│   │   │   ├── product_catalog_data_handler.py
│   │   │   ├── product_handler.py
│   │   │   ├── token_refresh.py
│   │   │   └── tokens.json
│   │   ├── dashboard
│   │   │   ├── app.py
│   │   │   ├── bandit.txt
│   │   │   ├── complexity.txt
│   │   │   ├── dump.rdb
│   │   │   ├── handlers
│   │   │   │   ├── accounts_handler.py
│   │   │   │   ├── auth_handler.py
│   │   │   │   ├── data_handler.py
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   ├── logs
│   │   │   │   └── flask.log
│   │   │   ├── requirements.txt
│   │   │   ├── service-account.json -> /home/oscar/ngn_board/config/service-account.json
│   │   │   ├── services
│   │   │   │   ├── cafe24_service.py
│   │   │   │   ├── catalog_sidebar_service.py
│   │   │   │   ├── data_service.py
│   │   │   │   ├── Fetch_Adset_Summary.py
│   │   │   │   ├── filter_service.py
│   │   │   │   ├── ga4_source_summary.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── insert_performance_summary.py
│   │   │   │   ├── meta_ads_insight.py
│   │   │   │   ├── meta_ads_preview.py
│   │   │   │   ├── meta_ads_service.py
│   │   │   │   ├── meta_ads_slide_collection.py
│   │   │   │   ├── meta_demo_handler.py
│   │   │   │   ├── meta_demo_service.py
│   │   │   │   ├── monthly_net_sales_visitors.py
│   │   │   │   ├── performance_summary.py
│   │   │   │   ├── platform_sales_summary.py
│   │   │   │   ├── product_sales_ratio.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_meta_ads_insight.py
│   │   │   │   └── viewitem_summary.py
│   │   │   ├── static
│   │   │   │   ├── demo_ads
│   │   │   │   │   ├── demo_1.jpg
│   │   │   │   │   ├── demo_2.jpg
│   │   │   │   │   ├── demo_3.jpg
│   │   │   │   │   ├── demo_4.jpg
│   │   │   │   │   ├── demo_5.jpg
│   │   │   │   │   ├── demo_6.jpg
│   │   │   │   │   ├── demo_7.jpg
│   │   │   │   │   └── demo_8.jpg
│   │   │   │   ├── img
│   │   │   │   │   ├── favicon.ico
│   │   │   │   │   └── x.png
│   │   │   │   ├── js
│   │   │   │   │   ├── cafe24_product_sales.js
│   │   │   │   │   ├── cafe24_sales.js
│   │   │   │   │   ├── catalog_sidebar.js
│   │   │   │   │   ├── common.js
│   │   │   │   │   ├── common_ui.js
│   │   │   │   │   ├── dashboard.js
│   │   │   │   │   ├── fetch_data.js
│   │   │   │   │   ├── filters.js
│   │   │   │   │   ├── ga4_source_summary.js
│   │   │   │   │   ├── loading_utils.js
│   │   │   │   │   ├── meta_ads_adset_summary_by_type.js
│   │   │   │   │   ├── meta_ads_insight_table.js
│   │   │   │   │   ├── meta_ads.js
│   │   │   │   │   ├── meta_ads_preview.js
│   │   │   │   │   ├── meta_ads_slide_collection.js
│   │   │   │   │   ├── meta_ads_state.js
│   │   │   │   │   ├── meta_ads_tags.js
│   │   │   │   │   ├── meta_ads_utils.js
│   │   │   │   │   ├── meta_demo.js
│   │   │   │   │   ├── monthly_net_sales_visitors.js
│   │   │   │   │   ├── pagination.js
│   │   │   │   │   ├── performance_monitor.js
│   │   │   │   │   ├── performance_summary.js
│   │   │   │   │   ├── platform_sales_monthly.js
│   │   │   │   │   ├── platform_sales_ratio.js
│   │   │   │   │   ├── platform_sales_summary.js
│   │   │   │   │   ├── product_sales_ratio.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── request_utils.js
│   │   │   │   │   ├── session_timeout.js
│   │   │   │   │   └── viewitem_summary.js
│   │   │   │   ├── sample
│   │   │   │   ├── styles.css
│   │   │   │   └── widgets
│   │   │   ├── templates
│   │   │   │   ├── ads_page.html
│   │   │   │   ├── components
│   │   │   │   │   ├── cafe24_product_sales_table.html
│   │   │   │   │   ├── cafe24_sales_table.html
│   │   │   │   │   ├── catalog_sidebar.html
│   │   │   │   │   ├── filters.html
│   │   │   │   │   ├── ga4_source_summary_table.html
│   │   │   │   │   ├── meta_ads_adset_summary_by_type_table.html
│   │   │   │   │   ├── meta_ads_insight_table.html
│   │   │   │   │   ├── meta_ads_preview_cards.html
│   │   │   │   │   ├── meta_ads_slide_collection_table.html
│   │   │   │   │   ├── meta_ads_table.html
│   │   │   │   │   ├── monthly_net_sales_visitors_chart.html
│   │   │   │   │   ├── performance_summary_table.html
│   │   │   │   │   ├── platform_sales_monthly.html
│   │   │   │   │   ├── platform_sales_ratio.html
│   │   │   │   │   ├── platform_sales_summary_table.html
│   │   │   │   │   ├── product_sales_ratio.html
│   │   │   │   │   └── viewitem_summary_table.html
│   │   │   │   ├── delete_info.html
│   │   │   │   ├── index.html
│   │   │   │   ├── login.html
│   │   │   │   ├── meta_demo.html
│   │   │   │   ├── privacy.html
│   │   │   │   ├── README.md
│   │   │   │   └── terms.html
│   │   │   └── utils
│   │   │       ├── cache_utils.py
│   │   │       ├── date_utils.py
│   │   │       ├── __init__.py
│   │   │       └── query_utils.py
│   │   ├── GA4_API
│   │   │   ├── ga4_traffic_today.py
│   │   │   ├── ga4_viewitem_today.py
│   │   │   └── sheet_update_custom.py
│   │   ├── __init__.py
│   │   ├── logs
│   │   ├── meta_api
│   │   │   ├── adset_config.json
│   │   │   ├── dynamic_Ads_meta.py
│   │   │   ├── Merge_Meta_Ads_Summary.py
│   │   │   └── meta_ads_handler.py
│   │   ├── ngn.env -> /home/oscar/ngn_board/ngn.env
│   │   ├── period_filter.py
│   │   ├── queries
│   │   │   ├── custom_date_range.sql
│   │   │   ├── daily_query.py
│   │   │   ├── __init__.py
│   │   │   ├── period_filter.py
│   │   │   └── .period_filter.py.swp
│   │   └── service-account.json -> /home/oscar/ngn_board/service-account.json
│   ├── requirements.txt
│   └── service-account.json
├── PERFORMANCE_OPTIMIZATION.md
├── recollect_ga4_traffic_2025_12_26.sql
├── recollect_ga4_traffic_ngn_redistribute.sql
├── reprocess_daily_sales.sh
├── requirements.txt
├── service-account.json
├── static
│   └── demo_ads
├── test_ga4_api_recent_date.py
├── tokens.json
├── tools
│   ├── 29cm_best
│   │   ├── apply_clustering_final.sql
│   │   ├── apply_clustering_fixed.sql
│   │   ├── apply_clustering.sql
│   │   ├── apply_clustering_streaming_fix.sql
│   │   ├── BIGQUERY_COST_ANALYSIS.md
│   │   ├── check_scheduler.sh
│   │   ├── create_scheduler.sh
│   │   ├── deploy_29cm_jobs.sh
│   │   ├── optimize_table_clustering.sql
│   │   ├── output
│   │   │   ├── 29cm_best_20251224_025102.csv
│   │   │   └── 29cm_best_20251224_025102.json
│   │   ├── README_CHECK_SCHEDULER.md
│   │   ├── README_SCHEDULER_SETUP.md
│   │   └── test_29cm_best_local.py
│   ├── ably_crwal.py
│   ├── ai_report_test
│   │   ├── AI_ANALYSIS_README.md
│   │   ├── ai_analyst.py
│   │   ├── AI_REPORT_SCHEDULE.md
│   │   ├── bq_monthly_snapshot.py
│   │   ├── bq_monthly_snapshot.py.backup
│   │   ├── CHATGPT_ANALYSIS_REVIEW.md
│   │   ├── check_event_table.sql
│   │   ├── check_monthly_tables_simple.sql
│   │   ├── check_monthly_tables.sql
│   │   ├── check_query_cost.sql
│   │   ├── check_snapshot_date_range.sql
│   │   ├── check_snapshot_dates.py
│   │   ├── check_snapshot_json_structure.sql
│   │   ├── check_snapshot_query_cost_simple.sql
│   │   ├── check_snapshot_query_cost.sql
│   │   ├── CODE_REVIEW_AFTER_FIX.md
│   │   ├── CODE_REVIEW.md
│   │   ├── COMPATIBILITY_CHECK.md
│   │   ├── create_event_table_simple.sql
│   │   ├── create_event_table.sql
│   │   ├── diagnose_monthly_rollup_issue.sql
│   │   ├── fill_all_monthly_data.sql
│   │   ├── FINAL_CODE_REVIEW.md
│   │   ├── generate_monthly_report_from_snapshot.py
│   │   ├── __init__.py
│   │   ├── jobs
│   │   │   ├── cloudbuild.yaml
│   │   │   ├── deploy_analysis_fixed.sh
│   │   │   ├── DEPLOY_ISSUES_FIXED.md
│   │   │   ├── deploy_monthly_ai_analysis.sh
│   │   │   ├── deploy_monthly_rollup.sh
│   │   │   ├── deploy_monthly_snapshot.sh
│   │   │   ├── deploy_sheet_event_collector.sh
│   │   │   ├── fill_past_months.py
│   │   │   ├── monthly_ai_analysis_job.py
│   │   │   ├── monthly_rollup_job.py
│   │   │   ├── monthly_snapshot_job.py
│   │   │   └── sheet_event_collector.py
│   │   ├── judgement_guardrails.py
│   │   ├── MARKDOWN_RENDERING_CHECK.md
│   │   ├── SNAPSHOT_COST_ANALYSIS.md
│   │   ├── SNAPSHOT_DATA_SOURCES.md
│   │   ├── system_prompt_v44.txt
│   │   ├── test_12month.py
│   │   ├── test_ai_analysis_local.sh
│   │   ├── test_piscess_12.sh
│   │   ├── update_monthly_tables.sql
│   │   ├── verify_schema.sql
│   │   └── verify_snapshot_simple.py
│   └── __init__.py
├── update_cart_signup_only.py
├── URLLIB3_FIX_ANALYSIS.md
├── validate_piscess_2025_12_23.sql
├── VERIFY_CODE_IN_IMAGE.sh
└── .vscode
    └── settings.json
/home/oscar/ngn_homepage
├── 컨텐츠 상품
│   ├── 워터
│   │   ├── 워터영상.mp4
│   │   ├── 워터화보.png
│   │   └── 워터제품.png
│   ├── 의상
│   │   ├── 의상화보1.png
│   │   ├── 의상영상2.mp4
│   │   ├── 의상화보2.png
│   │   ├── 의상영상.mp4
│   │   ├── 의상클립.mp4
│   │   ├── 의상제품.png
│   │   └── 의상컷.png
│   ├── 신발
│   │   ├── 신발영상.mp4
│   │   ├── 신발전시샷.png
│   │   └── 신발제품샷.png
│   ├── 화장품
│   │   ├── 화장품영상.mp4
│   │   ├── 화장품화보.png
│   │   └── 화장품제품.png
│   ├── AI기술1.mp4
│   └── 아파트.mp4
├── about.html
├── about_mobile_backup.html
├── about_mobile.html
├── app
│   ├── app.py
│   ├── images
│   │   └── aaa1.png
│   └── static
│       └── video
│           ├── 누구나타이틀.gif
│           └── 누구나타이틀.mp4
├── base.html
├── build.bat
├── build.ps1
├── compress_assets.py
├── compression_log.txt
├── convert_full.py
├── convert_longer.py
├── convert_new.py
├── convert_simple.py
├── convert_video.py
├── create_manual_thumbnails.bat
├── css
│   ├── about.css
│   ├── about_mobile.css
│   ├── common.css
│   ├── index.css
│   ├── index_mobile.css
│   ├── portfolio.css
│   ├── portfolio_mobile.css
│   ├── proposal.css
│   ├── proposal_mobile.css
│   ├── services.css
│   ├── services_mobile.css
│   ├── style.css.backup
│   ├── survey.css
│   ├── survey_mobile.css
│   ├── technology.css
│   └── technology_mobile.css
├── deploy.sh
├── Dockerfile
├── .dockerignore
├── -files  Select-String aaa1
├── fix_image_paths.py
├── fix_structure.bat
├── fix_video_paths.py
├── generate_pdf.js
├── generate_pdf.py
├── generate_thumbnails.py
├── .github
│   └── workflows
│       └── deploy.yml
├── .gitignore
├── how a952ecf --name-only
├── how HEAD~1services.html
├── how HEADindex.html  Select-String advantages -Context 5
├── index.html
├── index_mobile.html
├── js
│   ├── main.js
│   └── survey.js
├── Makefile
├── portfolio.html
├── portfolio_mobile.html
├── .pre-commit-config.yaml
├── proposal.html
├── proposal_mobile.html
├── README.md
├── requirements.txt
├── robots.txt
├── scripts
│   └── organize_assets.sh
├── services.html
├── services_mobile.html
├── setup_cloudshell.sh
├── simple_build.bat
├── simple_copy.py
├── sitemap.xml
├── static
│   ├── css
│   │   ├── about.css
│   │   ├── about_mobile.css
│   │   ├── common.css
│   │   ├── index.css
│   │   ├── index_mobile.css
│   │   ├── portfolio.css
│   │   ├── portfolio_mobile.css
│   │   ├── proposal.css
│   │   ├── proposal_mobile.css
│   │   ├── services.css
│   │   ├── services_mobile.css
│   │   ├── survey.css
│   │   ├── survey_mobile.css
│   │   ├── technology.css
│   │   ├── technology_mobile.css
│   │   └── technology_mobile_new.css
│   ├── css_backup_20250905
│   │   ├── about.css
│   │   ├── about_mobile.css
│   │   ├── common.css
│   │   ├── index.css
│   │   ├── index_mobile.css
│   │   ├── portfolio.css
│   │   ├── portfolio_mobile.css
│   │   ├── proposal.css
│   │   ├── proposal_mobile.css
│   │   ├── services.css
│   │   ├── services_mobile.css
│   │   ├── survey.css
│   │   ├── survey_mobile.css
│   │   ├── technology.css
│   │   ├── technology_mobile.css
│   │   └── technology_mobile_new.css
│   ├── img
│   │   ├── icons
│   │   │   ├── instagram.webp
│   │   │   ├── logo2.webp
│   │   │   ├── search.webp
│   │   │   └── x.webp
│   │   ├── portfolio
│   │   │   ├── 카타5.webp
│   │   │   ├── 90s.webp
│   │   │   ├── cata1.webp
│   │   │   ├── cata2.webp
│   │   │   ├── catalog5.webp
│   │   │   ├── clothes_cut.webp
│   │   │   ├── clothes_product.webp
│   │   │   ├── cosmetic_photo.webp
│   │   │   ├── cosmetic_product.webp
│   │   │   ├── jcc.webp
│   │   │   ├── jc.webp
│   │   │   ├── oscar.webp
│   │   │   ├── shoes_display.webp
│   │   │   ├── shoes_product.webp
│   │   │   ├── water_photo.webp
│   │   │   ├── water_product.webp
│   │   │   ├── 신발전시샷.webp
│   │   │   ├── 신발제품샷.webp
│   │   │   ├── 화장품제품.webp
│   │   │   ├── 화장품화보.webp
│   │   │   ├── 워터화보.webp
│   │   │   ├── 워터제품.webp
│   │   │   ├── 의상제품.webp
│   │   │   └── 의상컷.webp
│   │   └── ui
│   │       ├── 배경0816.webp
│   │       ├── 구글1.webp
│   │       ├── 기하1.webp
│   │       ├── 핵1.webp
│   │       ├── 배경2.webp
│   │       ├── 구글2.webp
│   │       ├── 기하2.webp
│   │       ├── 핵2.webp
│   │       ├── 구글3.webp
│   │       ├── 기하3.webp
│   │       ├── 핵3.webp
│   │       ├── 구글4.webp
│   │       ├── 핵4.webp
│   │       ├── aa1.webp
│   │       ├── aa2.webp
│   │       ├── aa3.webp
│   │       ├── aaa1.webp
│   │       ├── aaa2.webp
│   │       ├── aaa3.webp
│   │       ├── aw2.webp
│   │       ├── aw3.webp
│   │       ├── aw4.webp
│   │       ├── aw.webp
│   │       ├── background0816.webp
│   │       ├── background2.webp
│   │       ├── core1.webp
│   │       ├── core2.webp
│   │       ├── core3.webp
│   │       ├── core4.webp
│   │       ├── dash1.webp
│   │       ├── dash2.webp
│   │       ├── dash3.webp
│   │       ├── dash4.webp
│   │       ├── geometry1.webp
│   │       ├── geometry2.webp
│   │       ├── geometry3.webp
│   │       ├── google1.webp
│   │       ├── google2.webp
│   │       ├── google3.webp
│   │       ├── google4.webp
│   │       ├── popart_image.webp
│   │       ├── 팝아트이미지.webp
│   │       ├── why2.webp
│   │       └── why.webp
│   ├── js
│   │   ├── main.js
│   │   └── survey.js
│   ├── thumbs
│   │   ├── 카타1.jpg
│   │   ├── 카타1.webp
│   │   ├── con_main.jpg
│   │   ├── d1.jpg
│   │   ├── h1.jpg
│   │   ├── h2.jpg
│   │   ├── h2.webp
│   │   ├── 카탈로그.jpg
│   │   ├── K1.jpg
│   │   ├── k2.jpg
│   │   ├── K3.jpg
│   │   ├── K4.jpg
│   │   ├── main._ngn3.jpg
│   │   ├── main._ngn4.webp
│   │   ├── main._ngn.jpg
│   │   ├── net.jpg
│   │   ├── sns11.webp
│   │   └── sns1.jpg
│   └── videos
│       ├── content_products
│       │   ├── ai_tech1.mp4
│       │   ├── ai_tech1.webm
│       │   ├── apartment.mp4
│       │   ├── apartment.webm
│       │   ├── clothes
│       │   │   ├── clothes_clip.mp4
│       │   │   ├── clothes_clip.webm
│       │   │   ├── clothes_video2.mp4
│       │   │   ├── clothes_video2.webm
│       │   │   ├── clothes_video.mp4
│       │   │   └── clothes_video.webm
│       │   ├── cosmetics
│       │   │   ├── cosmetic_video.mp4
│       │   │   └── cosmetic_video.webm
│       │   ├── shoes
│       │   │   ├── shoes_video.mp4
│       │   │   └── shoes_video.webm
│       │   └── water
│       │       ├── water_video.mp4
│       │       └── water_video.webm
│       ├── hero
│       │   ├── d1.mp4
│       │   ├── d1.webm
│       │   ├── h1.mp4
│       │   ├── h1.webm
│       │   ├── h2.mp4
│       │   ├── h2.webm
│       │   ├── K1.mp4
│       │   ├── K1.webm
│       │   ├── k2.mp4
│       │   ├── k2.webm
│       │   ├── K3.mp4
│       │   ├── K3.webm
│       │   ├── K4.mp4
│       │   ├── K4.webm
│       │   ├── main2.mp4
│       │   ├── main2.webm
│       │   ├── main.mp4
│       │   ├── main._ngn3.mp4
│       │   ├── main._ngn3.webm
│       │   ├── main._ngn4.mp4
│       │   ├── main._ngn4.webm
│       │   ├── main.webm
│       │   ├── net.mp4
│       │   ├── net.webm
│       │   ├── sns11.mp4
│       │   ├── sns11.webm
│       │   ├── sns1.mp4
│       │   └── sns1.webm
│       ├── portfolio
│       │   ├── 카타1.mp4
│       │   ├── 카타1.webm
│       │   ├── apt.mp4
│       │   ├── apt.webm
│       │   ├── catalog1.mp4
│       │   ├── catalog1.webm
│       │   ├── catalog_main.mp4
│       │   ├── catalog_main.webm
│       │   ├── con_main.mp4
│       │   ├── con_main.webm
│       │   ├── 팝아트영상.mp4
│       │   ├── popart_video.mp4
│       │   ├── popart_video.webm
│       │   └── 팝아트영상.webm
│       └── ui
│           ├── ngn_title.gif
│           ├── ngn_title.mp4
│           └── ngn_title.webm
├── static_src
│   ├── img
│   │   ├── icons
│   │   │   ├── instagram.png
│   │   │   ├── logo2.png
│   │   │   ├── search.png
│   │   │   └── x.png
│   │   ├── portfolio
│   │   │   ├── 90s.png
│   │   │   ├── cata1.png
│   │   │   ├── cata2.png
│   │   │   ├── catalog5.png
│   │   │   ├── clothes_cut.png
│   │   │   ├── clothes_product.png
│   │   │   ├── cosmetic_photo.png
│   │   │   ├── cosmetic_product.png
│   │   │   ├── jcc.png
│   │   │   ├── jc.png
│   │   │   ├── oscar.png
│   │   │   ├── shoes_display.png
│   │   │   ├── shoes_product.png
│   │   │   ├── water_photo.png
│   │   │   └── water_product.png
│   │   └── ui
│   │       ├── aa1.png
│   │       ├── aa2.png
│   │       ├── aa3.png
│   │       ├── aaa1.png
│   │       ├── aaa2.png
│   │       ├── aaa3.png
│   │       ├── aw2.png
│   │       ├── aw3.png
│   │       ├── aw4.png
│   │       ├── aw.png
│   │       ├── background0816.png
│   │       ├── background2.png
│   │       ├── core1.png
│   │       ├── core2.png
│   │       ├── core3.png
│   │       ├── core4.png
│   │       ├── dash1.png
│   │       ├── dash2.png
│   │       ├── dash3.png
│   │       ├── dash4.png
│   │       ├── geometry1.png
│   │       ├── geometry2.png
│   │       ├── geometry3.png
│   │       ├── google1.png
│   │       ├── google2.png
│   │       ├── google3.png
│   │       ├── google4.png
│   │       ├── popart_image.png
│   │       ├── why2.png
│   │       └── why.png
│   └── videos_src
│       ├── content_products
│       │   ├── ai_tech1.mp4
│       │   ├── apartment.mp4
│       │   ├── clothes
│       │   │   ├── clothes_clip.mp4
│       │   │   ├── clothes_cut.png
│       │   │   ├── clothes_photo1.png
│       │   │   ├── clothes_photo2.png
│       │   │   ├── clothes_product.png
│       │   │   ├── clothes_video2.mp4
│       │   │   └── clothes_video.mp4
│       │   ├── cosmetics
│       │   │   ├── cosmetic_photo.png
│       │   │   ├── cosmetic_product.png
│       │   │   └── cosmetic_video.mp4
│       │   ├── shoes
│       │   │   ├── shoes_display.png
│       │   │   ├── shoes_product.png
│       │   │   └── shoes_video.mp4
│       │   └── water
│       │       ├── water_photo.png
│       │       ├── water_product.png
│       │       └── water_video.mp4
│       ├── hero
│       │   ├── d1.mp4
│       │   ├── h1.mp4
│       │   ├── h2.mp4
│       │   ├── K1.mp4
│       │   ├── k2.mp4
│       │   ├── K3.mp4
│       │   ├── K4.mp4
│       │   ├── main2._ngn.mp4
│       │   ├── main._ngn3.mp4
│       │   ├── main._ngn4.mp4
│       │   ├── main._ngn.mp4
│       │   ├── net.mp4
│       │   ├── sns11.mp4
│       │   └── sns1.mp4
│       ├── portfolio
│       │   ├── apt.mp4
│       │   ├── catalog1.mp4
│       │   ├── catalog_main.mp4
│       │   ├── con_main.mp4
│       │   └── popart_video.mp4
│       └── ui
│           ├── ngn_title.gif
│           └── ngn_title.mp4
├── survey.html
├── survey_mobile.html
├── sync_css.bat
├── technology.html
├── technology_mobile.html
└── upload_guide.md

124 directories, 935 files
```
