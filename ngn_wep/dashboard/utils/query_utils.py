def get_date_filter(period, start_date=None, end_date=None, table_alias="", column="order_date"):
    column_ref = f"{table_alias}.{column}" if table_alias else column

    if period is None or period == "today":
        return f"DATE(TIMESTAMP({column_ref})) = CURRENT_DATE()"
    elif period == "yesterday":
        return f"DATE(TIMESTAMP({column_ref})) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)"
    elif period == "last7days":
        return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 6 DAY) AND CURRENT_DATE()"
    elif period == "current_month":
        return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE_TRUNC(CURRENT_DATE(), MONTH) AND CURRENT_DATE()"
    elif period == "last_month":
        return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH) AND DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 DAY)"
    elif period == "manual":
        if start_date and end_date:
            return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE('{start_date}') AND DATE('{end_date}')"
        else:
            return ""  # ⛔️ 날짜 조건 아예 없음
    else:
        return f"DATE(TIMESTAMP({column_ref})) = CURRENT_DATE()"
