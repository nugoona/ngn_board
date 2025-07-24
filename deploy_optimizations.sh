#!/bin/bash

# =====================================
# NGN Dashboard 성능 최적화 배포 스크립트
# =====================================

set -e  # 에러 발생 시 스크립트 중단

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 환경 변수 확인
check_environment() {
    log "환경 변수 확인 중..."
    
    required_vars=("GOOGLE_APPLICATION_CREDENTIALS" "FLASK_APP" "FLASK_ENV")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            warn "$var 환경 변수가 설정되지 않음"
        else
            info "$var: ${!var}"
        fi
    done
}

# Redis 설치 및 설정
setup_redis() {
    log "Redis 설치 및 설정 중..."
    
    # Redis 설치 확인
    if ! command -v redis-server &> /dev/null; then
        info "Redis 설치 중..."
        
        # Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y redis-server
        # CentOS/RHEL
        elif command -v yum &> /dev/null; then
            sudo yum install -y redis
        # macOS
        elif command -v brew &> /dev/null; then
            brew install redis
        else
            error "지원하지 않는 운영체제입니다. Redis를 수동으로 설치해주세요."
        fi
    else
        info "Redis가 이미 설치되어 있습니다."
    fi
    
    # Redis 서비스 시작
    if systemctl is-active --quiet redis; then
        info "Redis 서비스가 실행 중입니다."
    else
        info "Redis 서비스 시작 중..."
        sudo systemctl start redis
        sudo systemctl enable redis
    fi
    
    # Redis 연결 테스트
    if redis-cli ping | grep -q "PONG"; then
        log "Redis 연결 테스트 성공"
    else
        error "Redis 연결 실패"
    fi
}

# Python 의존성 설치
install_dependencies() {
    log "Python 의존성 설치 중..."
    
    # 가상환경 활성화 (존재하는 경우)
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        info "가상환경 활성화됨"
    fi
    
    # requirements.txt 설치
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        log "의존성 설치 완료"
    else
        warn "requirements.txt 파일을 찾을 수 없습니다."
    fi
}

# 기존 Flask 프로세스 종료
stop_flask() {
    log "기존 Flask 프로세스 종료 중..."
    
    # Flask 프로세스 찾기 및 종료
    if pgrep -f "flask\|gunicorn\|ngn_wep.dashboard.app" > /dev/null; then
        pkill -f "flask\|gunicorn\|ngn_wep.dashboard.app"
        sleep 2
        info "기존 Flask 프로세스 종료됨"
    else
        info "실행 중인 Flask 프로세스 없음"
    fi
    
    # Python 캐시 파일 정리
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    log "캐시 파일 정리 완료"
}

# 캐시 워밍업
warm_cache() {
    log "캐시 워밍업 시작..."
    
    # Flask 앱이 실행될 때까지 대기
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:8080/dashboard/cache/stats > /dev/null; then
            break
        fi
        info "Flask 앱 시작 대기 중... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        warn "Flask 앱 시작 대기 시간 초과. 캐시 워밍업 건너뜀."
        return
    fi
    
    # 주요 엔드포인트 호출하여 캐시 워밍업
    local endpoints=(
        "/dashboard/get_data"
    )
    
    for endpoint in "${endpoints[@]}"; do
        info "캐시 워밍업: $endpoint"
        curl -s -X POST \
             -H "Content-Type: application/json" \
             -d '{"data_type":"all","period":"today"}' \
             "http://localhost:8080$endpoint" > /dev/null || warn "$endpoint 워밍업 실패"
    done
    
    log "캐시 워밍업 완료"
}

# 성능 테스트
performance_test() {
    log "성능 테스트 시작..."
    
    # Apache Bench 설치 확인
    if ! command -v ab &> /dev/null; then
        info "Apache Bench 설치 중..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y apache2-utils
        elif command -v yum &> /dev/null; then
            sudo yum install -y httpd-tools
        else
            warn "Apache Bench를 설치할 수 없습니다. 성능 테스트 건너뜀."
            return
        fi
    fi
    
    # 성능 테스트 실행
    info "동시 요청 테스트 (10개 요청, 동시성 2)"
    ab -n 10 -c 2 -T 'application/json' \
       -p <(echo '{"data_type":"performance_summary","period":"today"}') \
       http://localhost:8080/dashboard/get_data
    
    log "성능 테스트 완료"
}

# 배포 검증
verify_deployment() {
    log "배포 검증 시작..."
    
    # 헬스체크
    local health_check_url="http://localhost:8080/"
    if curl -s "$health_check_url" > /dev/null; then
        info "✅ 헬스체크 통과"
    else
        error "❌ 헬스체크 실패"
    fi
    
    # 캐시 상태 확인
    local cache_stats=$(curl -s http://localhost:8080/dashboard/cache/stats)
    if echo "$cache_stats" | grep -q '"enabled":true'; then
        info "✅ 캐시 시스템 활성화됨"
    else
        warn "⚠️ 캐시 시스템 비활성화됨"
    fi
    
    # API 응답 시간 측정
    local start_time=$(date +%s%N)
    curl -s -X POST \
         -H "Content-Type: application/json" \
         -d '{"data_type":"performance_summary","period":"today"}' \
         http://localhost:8080/dashboard/get_data > /dev/null
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 ))
    
    info "API 응답 시간: ${response_time}ms"
    
    if [[ $response_time -lt 2000 ]]; then
        info "✅ API 응답 시간 양호"
    else
        warn "⚠️ API 응답 시간이 느림 (${response_time}ms)"
    fi
    
    log "배포 검증 완료"
}

# Flask 앱 시작
start_flask() {
    log "Flask 앱 시작 중..."
    
    # 환경 변수 설정
    export FLASK_APP="ngn_wep.dashboard.app:app"
    export FLASK_ENV="production"
    export PYTHONPATH="/app:/app/ngn_wep/dashboard"
    
    # 개발 모드 vs 프로덕션 모드
    if [[ "${FLASK_ENV}" == "development" ]]; then
        info "개발 모드로 Flask 시작"
        nohup flask run --host=0.0.0.0 --port=8080 > flask.log 2>&1 &
    else
        info "프로덕션 모드로 Gunicorn 시작"
        nohup gunicorn \
            -w 2 \
            --threads 4 \
            --timeout 120 \
            --log-level info \
            --bind 0.0.0.0:8080 \
            --access-logfile access.log \
            --error-logfile error.log \
            ngn_wep.dashboard.app:app > gunicorn.log 2>&1 &
    fi
    
    local flask_pid=$!
    info "Flask PID: $flask_pid"
    
    # 시작 확인
    sleep 5
    if ps -p $flask_pid > /dev/null; then
        log "Flask 앱 시작 성공"
    else
        error "Flask 앱 시작 실패"
    fi
}

# 모니터링 설정
setup_monitoring() {
    log "모니터링 설정 중..."
    
    # 로그 로테이션 설정
    cat > /tmp/ngn-dashboard-logrotate << EOF
/app/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        pkill -USR1 -f gunicorn || true
    endscript
}
EOF
    
    if [[ -d "/etc/logrotate.d" ]]; then
        sudo cp /tmp/ngn-dashboard-logrotate /etc/logrotate.d/ngn-dashboard
        info "로그 로테이션 설정 완료"
    fi
    
    # 시스템 서비스 등록 (선택사항)
    if [[ "$1" == "--install-service" ]]; then
        info "시스템 서비스 등록 중..."
        
        cat > /tmp/ngn-dashboard.service << EOF
[Unit]
Description=NGN Dashboard
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/app
Environment=FLASK_APP=ngn_wep.dashboard.app:app
Environment=FLASK_ENV=production
Environment=PYTHONPATH=/app:/app/ngn_wep/dashboard
ExecStart=/usr/local/bin/gunicorn -w 2 --threads 4 --timeout 120 --bind 0.0.0.0:8080 ngn_wep.dashboard.app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF
        
        sudo cp /tmp/ngn-dashboard.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable ngn-dashboard
        info "시스템 서비스 등록 완료"
    fi
}

# 백업 생성
create_backup() {
    log "백업 생성 중..."
    
    local backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 중요 파일들 백업
    local backup_files=(
        "ngn_wep/dashboard/handlers/"
        "ngn_wep/dashboard/services/"
        "ngn_wep/dashboard/static/"
        "ngn_wep/dashboard/templates/"
        "requirements.txt"
    )
    
    for file in "${backup_files[@]}"; do
        if [[ -e "$file" ]]; then
            cp -r "$file" "$backup_dir/"
        fi
    done
    
    # 백업 압축
    tar -czf "${backup_dir}.tar.gz" "$backup_dir"
    rm -rf "$backup_dir"
    
    log "백업 생성 완료: ${backup_dir}.tar.gz"
}

# 메인 배포 함수
deploy() {
    log "========================================="
    log "NGN Dashboard 성능 최적화 배포 시작"
    log "========================================="
    
    # 백업 생성
    create_backup
    
    # 환경 확인
    check_environment
    
    # Redis 설정
    setup_redis
    
    # 의존성 설치
    install_dependencies
    
    # 기존 프로세스 종료
    stop_flask
    
    # Flask 앱 시작
    start_flask
    
    # 캐시 워밍업
    warm_cache
    
    # 성능 테스트
    performance_test
    
    # 배포 검증
    verify_deployment
    
    # 모니터링 설정
    setup_monitoring "$1"
    
    log "========================================="
    log "배포 완료! 🎉"
    log "========================================="
    
    info "접속 URL: http://localhost:8080"
    info "캐시 상태: http://localhost:8080/dashboard/cache/stats"
    info "로그 파일: $(pwd)/gunicorn.log, $(pwd)/error.log"
    
    # 최종 상태 출력
    echo ""
    log "시스템 상태:"
    info "Redis: $(systemctl is-active redis 2>/dev/null || echo 'Unknown')"
    info "Flask: $(pgrep -f 'flask\|gunicorn' > /dev/null && echo 'Running' || echo 'Stopped')"
    info "메모리 사용량: $(free -h | grep Mem | awk '{print $3"/"$2}')"
    info "디스크 사용량: $(df -h . | tail -1 | awk '{print $3"/"$2" ("$5")"}')"
}

# 스크립트 사용법
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --install-service    시스템 서비스로 등록"
    echo "  --skip-redis        Redis 설정 건너뛰기"
    echo "  --skip-test         성능 테스트 건너뛰기"
    echo "  --help              도움말 표시"
    echo ""
    echo "예제:"
    echo "  $0                   기본 배포"
    echo "  $0 --install-service 서비스 등록과 함께 배포"
}

# 메인 실행
main() {
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        *)
            deploy "$1"
            ;;
    esac
}

# 스크립트가 직접 실행된 경우에만 main 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 