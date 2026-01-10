import os, re, time, requests, urllib.parse
from io import BytesIO
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ultralytics import YOLO

# ─────────────────────── 설정 ───────────────────────
# 육육걸즈 테스트 URL
URL = "https://66girls.co.kr/product/%EB%B0%8D%ED%81%AC%ED%8D%BC%EC%B9%B4%EB%9D%BC%EC%9E%90%EC%BC%93/158610/category/108/display/1/"

# 요청하신 절대 경로로 수정
OUT_DIR = r"D:\github\ngn_dashboard\ngn_wep\ad_make\test_crop" 
os.makedirs(OUT_DIR, exist_ok=True)

# 속도와 비용 절감을 위해 Nano 모델 사용
model = YOLO("yolov8n.pt") 

# ─────────────────────── 이미지 수집 ───────────────────────
def fetch_detail_imgs(page_url: str) -> list[str]:
    parsed_url = urllib.parse.urlparse(page_url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    drv.get(page_url)
    time.sleep(2)
    soup = BeautifulSoup(drv.page_source, "html.parser")
    drv.quit()

    urls = []
    # 육육걸즈 및 범용 쇼핑몰 선택자 통합
    selectors = [".cont img", "#prdDetail img", "#prdDetailContent img", "#prdDetailContentLazy img"]
    
    found_tags = []
    for sel in selectors:
        found_tags = soup.select(sel)
        if found_tags: break

    for tag in found_tags:
        src = tag.get("ec-data-src") or tag.get("data-original") or tag.get("src", "")
        if not src or src.startswith("data:") or any(x in src for x in ["/small/", "/thumb", ".gif"]):
            continue
        if src.startswith("//"): src = "https:" + src
        elif src.startswith("/"): src = base_domain + src
        if src not in urls: urls.append(src)
    return urls

# ─────────────────────── 상품명 추출 ───────────────────────
def safe_product_name(url: str) -> str:
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        meta = soup.find("meta", {"property": "og:title"}) or soup.find("title")
        raw = meta.get("content") if meta and meta.has_attr("content") else meta.text if meta else url.split("/")[-2]
        cleaned = re.sub(r"[^A-Za-z0-9가-힣]+", "_", raw).strip("_")
        # 브랜드 제거 키워드 통합
        for kw in ["_육육걸즈_66GIRLS", "_파이시스_PISCESS", "_66걸즈"]:
            cleaned = cleaned.replace(kw, "")
        return cleaned
    except:
        return "product_" + str(int(time.time()))

# ─────────────────────── 좌우 흰 여백 제거 ───────────────────────
def trim_white_sides(image: Image.Image) -> Image.Image:
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg).convert("L")
    bbox = diff.getbbox()
    if bbox:
        x1, y1, x2, y2 = bbox
        return image.crop((x1, 0, x2, image.height))
    return image

# ─────────────────────── YOLO 슬라이싱 ───────────────────────
def smart_slice_by_yolo(img: Image.Image, base_name: str, used_names: set) -> int:
    if img.width > img.height * 2.5:
        print("📏 가로로 너무 넓은 배너 이미지 → 건너뜀")
        return 0

    # imgsz를 1024로 높여 긴 상세이미지 내 작은 인물도 잘 잡게 함
    results = model.predict(img, conf=0.25, imgsz=1024, verbose=False)
    boxes = results[0].boxes
    if not boxes:
        print("❌ 감지된 박스 없음")
        return 0

    xyxy_list = boxes.xyxy.cpu().numpy()
    xyxy_list = sorted(xyxy_list, key=lambda box: box[1])
    saved = 0

    for box in xyxy_list:
        x1, y1, x2, y2 = map(int, box[:4])
        if (y2 - y1) < 150: # 너무 작은 영역은 광고 품질 저하로 제외
            continue
            
        # 상하 여백을 5% 정도 추가하여 안정감 확보
        h_margin = int((y2 - y1) * 0.05)
        y1_final = max(0, y1 - h_margin)
        y2_final = min(img.height, y2 + h_margin)
            
        cropped = img.crop((0, y1_final, img.width, y2_final))
        cropped = trim_white_sides(cropped)

        crop_ratio = cropped.width / cropped.height
        # 66걸즈 같은 세로형 샷을 위해 비율 허용 범위를 0.5~1.5로 완화
        if not (0.5 <= crop_ratio <= 1.5):
            print(f"⛔ 비율 미달 (ratio={crop_ratio:.2f}) → 건너뜀")
            continue

        # 파일명 중복 방지 인덱스 계산
        existing_nums = []
        for name in used_names:
            match = re.search(rf"^{re.escape(base_name)}_(\d+)\.jpg$", name)
            if match:
                existing_nums.append(int(match.group(1)))
        
        next_index = max(existing_nums, default=0) + 1

        fname = f"{base_name}_{next_index}.jpg"
        cropped.save(os.path.join(OUT_DIR, fname), quality=95)
        used_names.add(fname)
        print(f"💾 저장 완료: {fname}")
        saved += 1

        if saved >= 12:
            print("🛑 슬라이스 최대치 도달")
            break

    return saved

# ─────────────────────── 실행 ───────────────────────
def run(page_url: str):
    imgs = fetch_detail_imgs(page_url)
    if not imgs:
        raise RuntimeError("❌ 이미지 없음")

    pname = safe_product_name(page_url)
    print("📦 상품명:", pname)
    # 지정된 경로의 기존 파일 로드하여 중복 방지
    used_names = set(os.listdir(OUT_DIR))

    # 속도를 위해 상위 15개 이미지만 정밀 분석
    for seq, url in enumerate(imgs[:15], 1):
        print(f"\n[{seq}] 이미지 다운로드 → {url}")
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGB")
        except Exception as e:
            print(f"⚠️ 이미지 처리 실패: {e}")
            continue

        saved = smart_slice_by_yolo(img, pname, used_names)
        if saved == 0:
            print("⚠️ YOLO 슬라이싱 실패 또는 조건 미달")

    print("\n✅ 전체 완료. 저장 위치:", OUT_DIR)

if __name__ == "__main__":
    run(URL)