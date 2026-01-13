"""
이미지 추출 및 YOLO 크롭 로직
- 원본 로컬 코드 기반으로 Cloud Run 최적화
"""
import os
import re
import time
import base64
import urllib.parse
from io import BytesIO

import requests
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# YOLO 모델 (Nano - 속도/비용 최적화)
from ultralytics import YOLO

model = None


def get_model():
    """YOLO 모델 싱글톤 로드"""
    global model
    if model is None:
        print("[INFO] YOLO 모델 로딩...")
        model = YOLO("yolov8n.pt")
    return model


def pil_to_base64(img: Image.Image, quality: int = 90) -> str:
    """PIL 이미지를 Base64 문자열로 변환"""
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=quality)
    b64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def trim_white_sides(image: Image.Image) -> Image.Image:
    """좌우 흰 여백 제거"""
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg).convert("L")
    bbox = diff.getbbox()
    if bbox:
        return image.crop((bbox[0], 0, bbox[2], image.height))
    return image


def fetch_detail_images(page_url: str, selectors: list) -> list:
    """Selenium으로 상세페이지 이미지 URL 수집"""
    parsed_url = urllib.parse.urlparse(page_url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Chrome 옵션 설정 (원본과 동일)
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")

    # Cloud Run 환경
    chrome_bin = os.environ.get("CHROME_BIN", "/usr/bin/google-chrome")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

    if os.path.exists(chrome_bin):
        opt.binary_location = chrome_bin

    try:
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            # 폴백: webdriver_manager 사용
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())

        drv = webdriver.Chrome(service=service, options=opt)
    except Exception as e:
        print(f"[ERROR] Chrome 초기화 실패: {e}")
        return []

    try:
        print(f"[INFO] 페이지 로딩: {page_url}")
        drv.get(page_url)
        time.sleep(2)  # 페이지 로딩 대기

        # 스크롤로 lazy loading 트리거
        drv.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        drv.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        soup = BeautifulSoup(drv.page_source, "html.parser")
    except Exception as e:
        print(f"[ERROR] 페이지 로딩 실패: {e}")
        return []
    finally:
        drv.quit()

    urls = []
    found_tags = []

    # 선택자 순회하며 이미지 찾기
    for sel in selectors:
        found_tags = soup.select(sel)
        if found_tags:
            print(f"[INFO] 선택자 '{sel}'에서 {len(found_tags)}개 태그 발견")
            break

    if not found_tags:
        print(f"[WARN] 어떤 선택자로도 이미지를 찾지 못함")
        print(f"[DEBUG] 시도한 선택자: {selectors}")

    for tag in found_tags:
        # 다양한 src 속성 체크 (원본과 동일한 순서)
        src = (
            tag.get("ec-data-src") or
            tag.get("data-original") or
            tag.get("src", "")
        )

        if not src or src.startswith("data:"):
            continue

        # 썸네일/아이콘 제외 (원본과 동일)
        if any(x in src for x in ["/small/", "/thumb", ".gif"]):
            continue

        # URL 정규화
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = base_domain + src

        if src not in urls:
            urls.append(src)
            print(f"[DEBUG] 이미지 URL 추가: {src[:80]}...")

    print(f"[INFO] 총 {len(urls)}개 이미지 URL 수집됨")
    return urls


def extract_product_name(page_url: str, headers: dict) -> str:
    """상품명 추출"""
    try:
        res = requests.get(page_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            raw_name = og_title.get("content", "product")
        else:
            raw_name = soup.title.string if soup.title else "product"

        name = re.sub(r"[^A-Za-z0-9가-힣]+", "_", raw_name).strip("_")

        # 브랜드명 제거
        for kw in ["_육육걸즈_66GIRLS", "_파이시스_PISCESS", "_66걸즈", "_PISCESS"]:
            name = name.replace(kw, "")

        return name[:50]

    except Exception as e:
        print(f"[WARN] 상품명 추출 실패: {e}")
        return "product"


def smart_slice_by_yolo(img: Image.Image) -> list:
    """YOLO로 이미지에서 사람/상품 영역 감지 후 크롭"""
    results_data = []

    # 가로로 너무 긴 이미지 스킵 (배너 등)
    if img.width > img.height * 2.5:
        return results_data

    yolo = get_model()
    results = yolo.predict(img, conf=0.25, imgsz=1024, verbose=False)
    boxes = results[0].boxes

    if not boxes:
        return results_data

    # Y좌표 기준 정렬 (위에서 아래로)
    xyxy_list = sorted(boxes.xyxy.cpu().numpy(), key=lambda box: box[1])
    saved_count = 0

    for box in xyxy_list:
        x1, y1, x2, y2 = map(int, box[:4])

        # 너무 작은 영역 스킵
        if (y2 - y1) < 150:
            continue

        # 상하 마진 추가 (5%)
        h_margin = int((y2 - y1) * 0.05)
        y1_f = max(0, y1 - h_margin)
        y2_f = min(img.height, y2 + h_margin)

        # 전체 너비로 크롭
        cropped = img.crop((0, y1_f, img.width, y2_f))
        cropped = trim_white_sides(cropped)

        # 비율 체크 (정사각형에 가까운 것만)
        ratio = cropped.width / cropped.height
        if not (0.5 <= ratio <= 1.5):
            continue

        # Base64 data URL로 변환
        data_url = pil_to_base64(cropped)
        results_data.append({
            "data_url": data_url,
            "width": cropped.width,
            "height": cropped.height
        })

        saved_count += 1
        if saved_count >= 12:
            break

    return results_data


def extract_images_from_url(url: str, selectors: list) -> dict:
    """
    메인 추출 함수

    Returns:
        {
            "product_name": "상품명",
            "images": [{"data_url": "data:image/jpeg;base64,...", "width": 800, "height": 800}, ...]
        }
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": url
    }

    # 1. 상품명 추출
    product_name = extract_product_name(url, headers)
    print(f"[INFO] 상품명: {product_name}")

    # 2. 상세페이지 이미지 URL 수집
    img_urls = fetch_detail_images(url, selectors)
    print(f"[INFO] 발견된 이미지 URL 수: {len(img_urls)}")

    if not img_urls:
        print("[WARN] 이미지 URL을 찾지 못했습니다")
        return {"product_name": product_name, "images": []}

    # 3. 각 이미지 다운로드 및 YOLO 처리
    all_images = []
    fallback_images = []

    for seq, img_url in enumerate(img_urls[:15], 1):
        print(f"[{seq}] 처리 중: {img_url[:80]}...")

        try:
            response = requests.get(img_url, headers=headers, timeout=15)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content)).convert("RGB")
            print(f"    이미지 크기: {img.width}x{img.height}")

            # YOLO 크롭
            cropped_images = smart_slice_by_yolo(img)
            all_images.extend(cropped_images)

            # 폴백용: YOLO가 못 찾아도 원본 저장
            if not cropped_images and img.width >= 400 and img.height >= 400:
                ratio = img.width / img.height
                if 0.4 <= ratio <= 2.0 and len(fallback_images) < 8:
                    # 리사이즈
                    if img.width > 1200:
                        new_height = int(img.height * (1200 / img.width))
                        img = img.resize((1200, new_height), Image.LANCZOS)
                    fallback_images.append({
                        "data_url": pil_to_base64(img),
                        "width": img.width,
                        "height": img.height
                    })

            print(f"    -> {len(cropped_images)}개 크롭 생성")

        except Exception as e:
            print(f"    -> 오류: {e}")
            continue

    # YOLO 결과가 없으면 폴백 이미지 사용
    if not all_images and fallback_images:
        print(f"[INFO] YOLO 결과 없음, 폴백 이미지 {len(fallback_images)}개 사용")
        all_images = fallback_images

    print(f"[INFO] 총 {len(all_images)}개 이미지 추출 완료")

    return {
        "product_name": product_name,
        "images": all_images
    }
