import os, re, time, requests
from io import BytesIO
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ultralytics import YOLO

# ─────────────────────── 설정 ───────────────────────
URL = "https://piscess.shop/product/25fw-%EB%A6%AC%ED%8D%BC%EB%B8%8Cturn-up-waist-jogger-pantsbrown/1208/category/182/display/1/"
OUT_DIR = "output_yolo_slices"
os.makedirs(OUT_DIR, exist_ok=True)

model = YOLO("yolov8m.pt")

# ─────────────────────── 이미지 수집 ───────────────────────
def fetch_detail_imgs(page_url: str) -> list[str]:
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
    drv.get(page_url); time.sleep(2)
    soup = BeautifulSoup(drv.page_source, "html.parser"); drv.quit()

    urls = []
    for tag in soup.select("#prdDetailContentLazy img"):
        src = tag.get("data-original") or tag.get("ec-data-src") or tag.get("src", "")
        if not src or src.startswith("data:") or "/small/" in src or "/thumb" in src or src.endswith(".gif"):
            continue
        if src.startswith("//"): src = "https:" + src
        elif src.startswith("/"): src = "https://piscess.shop" + src
        urls.append(src)
    return urls

# ─────────────────────── 상품명 추출 ───────────────────────
def safe_product_name(url: str) -> str:
    soup = BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text, "html.parser")
    meta = soup.find("meta", {"property": "og:title"}) or soup.find("title")
    raw = meta.get("content") if meta and meta.has_attr("content") else meta.text if meta else url.split("/")[-2]
    cleaned = re.sub(r"[^A-Za-z0-9가-힣_]+", "_", raw).strip("_")
    return cleaned.replace("_파이시스_PISCESS", "")

# ─────────────────────── 좌우 흰 여백 제거 ───────────────────────
def trim_white_sides(image: Image.Image) -> Image.Image:
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg).convert("L")
    bbox = diff.getbbox()
    if bbox:
        x1, y1, x2, y2 = bbox
        return image.crop((x1, 0, x2, image.height))  # 상하는 유지, 좌우만 크롭
    return image

# ─────────────────────── YOLO 슬라이싱 ───────────────────────
def smart_slice_by_yolo(img: Image.Image, base_name: str, used_names: set) -> int:
    if img.width > img.height * 2.5:
        print("📏 가로로 너무 넓은 배너 이미지 → 건너뜀")
        return 0

    results = model.predict(img, conf=0.25, imgsz=1024, verbose=False)
    boxes = results[0].boxes
    if not boxes:
        print("❌ 감지된 박스 없음")
        return 0

    xyxy_list = boxes.xyxy.cpu().numpy()
    xyxy_list = sorted(xyxy_list, key=lambda box: box[1])
    saved = 0
    next_index = 1

    existing_nums = [int(re.search(rf"^{re.escape(base_name)}_(\d+)\.jpg$", name).group(1))
                     for name in used_names if re.match(rf"^{re.escape(base_name)}_\d+\.jpg$", name)]
    next_index = max(existing_nums, default=0) + 1

    for box in xyxy_list:
        x1, y1, x2, y2 = map(int, box[:4])
        if (y2 - y1) < 100:
            continue
        cropped = img.crop((0, y1, img.width, y2))
        cropped = trim_white_sides(cropped)  # ✅ 좌우 여백 제거

        crop_ratio = cropped.width / cropped.height
        if not (0.6 <= crop_ratio <= 1.4):
            print(f"⛔ 슬라이스 비율 미달 (ratio={crop_ratio:.2f}) → 건너뜀")
            continue

        while True:
            fname = f"{base_name}_{next_index}.jpg"
            if fname not in used_names:
                break
            next_index += 1

        cropped.save(os.path.join(OUT_DIR, fname), quality=95)
        used_names.add(fname)
        print(f"💾 저장 완료: {fname}")
        saved += 1
        next_index += 1

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
    used_names = set(os.listdir(OUT_DIR))

    for seq, url in enumerate(imgs, 1):
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
            print("⚠️ YOLO 슬라이싱 실패 또는 제외됨")

    print("\n✅ 전체 완료:", OUT_DIR)

if __name__ == "__main__":
    run(URL)
