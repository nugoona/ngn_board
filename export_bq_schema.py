#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigQuery 스키마 내보내기 스크립트
모든 데이터셋과 테이블의 스키마를 마크다운 파일로 저장합니다.
"""

import os
from google.cloud import bigquery
from datetime import datetime

# GCP 프로젝트 ID
PROJECT_ID = os.environ.get("GCP_PROJECT", "winged-precept-443218-v8")
OUTPUT_FILE = "bigquery_schemas.md"


def get_field_mode(field):
    """필드 모드 반환 (NULLABLE, REQUIRED, REPEATED)"""
    return field.mode if field.mode else "NULLABLE"


def get_field_description(field):
    """필드 설명 반환"""
    return field.description if field.description else ""


def format_field_type(field):
    """필드 타입 포맷팅 (중첩된 구조 포함)"""
    if field.field_type == "RECORD":
        # RECORD 타입의 경우 중첩 필드 정보 포함
        nested_fields = []
        for nested_field in field.fields:
            nested_fields.append(f"{nested_field.name}:{nested_field.field_type}")
        return f"RECORD<{', '.join(nested_fields)}>"
    return field.field_type


def export_table_schema(table):
    """테이블 스키마를 마크다운 형식으로 변환"""
    lines = []
    
    # 테이블명
    lines.append(f"### Table: `{table.table_id}`")
    lines.append("")
    
    # 테이블 설명
    if table.description:
        lines.append(f"**Description:** {table.description}")
        lines.append("")
    
    # 컬럼 정보 표 헤더
    lines.append("| 컬럼명 | 타입 | 모드 | 설명 |")
    lines.append("|--------|------|------|------|")
    
    # 컬럼 정보
    for field in table.schema:
        field_name = field.name
        field_type = format_field_type(field)
        field_mode = get_field_mode(field)
        field_desc = get_field_description(field)
        
        # 마크다운 표에서 파이프 문자 이스케이프
        field_desc = field_desc.replace("|", "\\|")
        
        lines.append(f"| `{field_name}` | `{field_type}` | `{field_mode}` | {field_desc} |")
    
    lines.append("")
    return "\n".join(lines)


def export_all_schemas():
    """모든 데이터셋과 테이블의 스키마를 내보냅니다."""
    print(f"🔍 BigQuery 프로젝트 '{PROJECT_ID}' 스키마 조회 중...")
    
    # BigQuery 클라이언트 생성
    client = bigquery.Client(project=PROJECT_ID)
    
    # 마크다운 내용 저장
    markdown_content = []
    
    # 문서 제목
    markdown_content.append("# BigQuery Schema Dictionary")
    markdown_content.append("")
    markdown_content.append(f"**프로젝트:** `{PROJECT_ID}`")
    markdown_content.append(f"**생성 일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    markdown_content.append("")
    markdown_content.append("---")
    markdown_content.append("")
    
    # 모든 데이터셋 조회
    datasets = list(client.list_datasets())
    
    if not datasets:
        print("⚠️ 데이터셋을 찾을 수 없습니다.")
        markdown_content.append("> 데이터셋이 없습니다.")
    else:
        print(f"📊 총 {len(datasets)}개의 데이터셋을 찾았습니다.")
        
        # 데이터셋별로 처리
        for dataset in datasets:
            dataset_id = dataset.dataset_id
            print(f"  📂 데이터셋: {dataset_id}")
            
            # 데이터셋 헤더
            markdown_content.append(f"## Dataset: `{dataset_id}`")
            markdown_content.append("")
            
            # 데이터셋 설명
            if dataset.description:
                markdown_content.append(f"**Description:** {dataset.description}")
                markdown_content.append("")
            
            # 데이터셋 내 모든 테이블 조회
            dataset_ref = client.dataset(dataset_id)
            tables = list(client.list_tables(dataset_ref))
            
            if not tables:
                markdown_content.append("> 테이블이 없습니다.")
                markdown_content.append("")
            else:
                print(f"    📋 테이블 {len(tables)}개 발견")
                
                for table_ref in tables:
                    table_id = table_ref.table_id
                    print(f"      🔍 테이블 스키마 조회: {dataset_id}.{table_id}")
                    
                    try:
                        # 테이블 객체 가져오기 (스키마 포함)
                        table = client.get_table(dataset_ref.table(table_id))
                        
                        # 테이블 스키마 마크다운 변환
                        table_markdown = export_table_schema(table)
                        markdown_content.append(table_markdown)
                        
                    except Exception as e:
                        print(f"      ❌ 테이블 '{table_id}' 스키마 조회 실패: {e}")
                        markdown_content.append(f"### Table: `{table_id}`")
                        markdown_content.append("")
                        markdown_content.append(f"> ⚠️ 스키마 조회 실패: {str(e)}")
                        markdown_content.append("")
            
            markdown_content.append("---")
            markdown_content.append("")
    
    # 마크다운 파일 저장
    output_path = os.path.join(os.getcwd(), OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_content))
    
    print(f"\n✅ 스키마 내보내기 완료!")
    print(f"📄 파일 저장 위치: {output_path}")
    print(f"📊 총 데이터셋: {len(datasets)}개")


if __name__ == "__main__":
    try:
        export_all_schemas()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

