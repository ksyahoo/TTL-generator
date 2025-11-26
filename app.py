import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
from rembg import remove
import requests

# --- 設定區 ---
CANVAS_WIDTH = 888
CANVAS_HEIGHT = 1020

# 設定頁面資訊
st.set_page_config(page_title="AI 電商圖卡生成器", layout="centered")

def load_font(font_file, size):
    if font_file is None:
        return ImageFont.load_default()
    try:
        # 複製 BytesIO，避免多次讀取導致指標錯誤
        font_bytes_copy = io.BytesIO(font_file.getvalue())
        return ImageFont.truetype(font_bytes_copy, size)
    except Exception as e:
        st.error(f"字型讀取失敗: {e}")
        return ImageFont.load_default()

def get_image_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        st.error(f"無法讀取圖片網址: {e}")
        return None

def get_darkest_color(img):
    try:
        small_img = img.resize((150, 150))
        rgb_img = small_img.convert("RGB")
        pixels = list(rgb_img.getdata())
        darkest = min(pixels, key=lambda p: 0.299*p[0] + 0.587*p[1] + 0.114*p[2])
        return '#{:02x}{:02x}{:02x}'.format(*darkest)
    except:
        return "#c94f3f"

def resize_keep_aspect(img, max_width, max_height):
    ratio = min(max_width / img.width, max_height / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)

def create_composite_image(bg_img, prod1_img, prod2_img, text1, text2, btn_text, font_source):
    # 1. 準備背景
    original_bg = bg_img
    bg = original_bg.convert("RGBA").resize((CANVAS_WIDTH, CANVAS_HEIGHT))
    draw = ImageDraw.Draw(bg)
    
    # 2. 計算背景最深顏色
    theme_color = get_darkest_color(original_bg)
    
    # 3. 繪製標題 (80px)
    font_title = load_font(font_source, 80)
    
    # 第一行
    text1_bbox = draw.textbbox((0, 0), text1, font=font_title)
    text1_w = text1_bbox[2] - text1_bbox[0]
    draw.text(((CANVAS_WIDTH - text1_w) / 2, 90), text1, font=font_title, fill="white")
    
    # 第二行
    text2_bbox = draw.textbbox((0, 0), text2, font=font_title)
    text2_w = text2_bbox[2] - text2_bbox[0]
    draw.text(((CANVAS_WIDTH - text2_w) / 2, 190), text2, font=font_title, fill="white")

    # 4. 處理商品圖 (AI 自動去背)
    prod_area_w = CANVAS_WIDTH * 0.8
    prod_area_h = CANVAS_HEIGHT * 0.4
    images = []
    
    with st.spinner('AI 正在幫商品去背中... (首次執行需下載模型，請稍候)'):
        if prod1_img:
            img1 = remove(prod1_img)
            images.append(img1)
        if prod2_img:
            img2 = remove(prod2_img)
            images.append(img2)
    
    # --- 位置與尺寸調整區 ---
    # 位置：維持 y=310
    start_y = 310
    
    # 尺寸：120%
    scale_factor_w = 0.84 
    scale_factor_h = 1.2 
    
    target_w = prod_area_w * scale_factor_w
    target_h = prod_area_h * scale_factor_h
    
    if len(images) >= 1:
        p1 = resize_keep_aspect(images[0], target_w, target_h)
        bg.paste(p1, (100, start_y), p1)
        
    if len(images) >= 2:
        p2 = resize_keep_aspect(images[1], target_w, target_h)
        bg.paste(p2, (CANVAS_WIDTH - p2.width - 80, start_y + 80), p2)

    # 5. 繪製按鈕 (4倍超取樣抗鋸齒)
    
    # 目標尺寸與位置
    btn_w, btn_h = 311, 91
    btn_x = int((CANVAS_WIDTH - btn_w) / 2 - 4)
    btn_y = 888
    
    # 設定超取樣倍率
    scale = 4 
    
    # 建立一個放大的透明畫布
    btn_img = Image.new('RGBA', (btn_w * scale, btn_h * scale), (0, 0, 0, 0))
    btn_draw = ImageDraw.Draw(btn_img)
    
    # 載入放大的字型
    font_btn_large = load_font(font_source, 48 * scale)
    
    # 繪製放大的圓角矩形
    btn_draw.rounded_rectangle(
        [(0, 0), (btn_w * scale, btn_h * scale)], 
        radius=(btn_h/2) * scale, 
        fill="white", 
        outline=theme_color, 
        width=3 * scale
    )
    
    # 計算放大的文字位置
    btn_text_bbox = btn_draw.textbbox((0, 0), btn_text, font=font_btn_large)
    btn_text_w = btn_text_bbox[2] - btn_text_bbox[0]
    btn_text_h = btn_text_bbox[3] - btn_text_bbox[1]
    
    text_x = (btn_w * scale - btn_text_w) / 2
    text_y = (btn_h * scale - btn_text_h) / 2 - (14 * scale) # 垂直位移放大
    
    # 繪製放大的文字
    btn_draw.text((text_x, text_y), btn_text, font=font_btn_large, fill=theme_color)
    
    # 將畫布縮小回原始尺寸 (平滑處理)
    btn_img_smooth = btn_img.resize((btn_w, btn_h), Image.Resampling.LANCZOS)
    
    # 貼回主圖
    bg.paste(btn_img_smooth, (btn_x, btn_y), btn_img_smooth)

    return bg, theme_color

# --- 圖片輸入輔助函式 ---
def image_input_area(label, key_prefix):
    st.subheader(label)
    tab1, tab2 = st.tabs(["📁 上傳檔案", "🔗 貼上網址"])
    
    img_data = None
    
    with tab1:
        uploaded = st.file_uploader(f"上傳 {label}", type=["jpg", "png", "jpeg"], key=f"{key_prefix}_up")
        if uploaded:
            img_data = Image.open(uploaded)
            
    with tab2:
        url = st.text_input(f"貼上 {label} 網址", key=f"{key_prefix}_url")
        if url:
            img_data = get_image_from_url(url)
            
    return img_data

# --- Streamlit 介面 ---
st.title("AI 電商圖卡生成器 - TTL")

# 側邊欄：上傳字型
st.sidebar.header("1. 字型設定 (必要)")
st.sidebar.info("請上傳字型檔 (如 msjh.ttc)。")
font_upload = st.sidebar.file_uploader("上傳 .ttf / .otf / .ttc 檔", type=["ttf", "otf", "ttc"])

st.header("2. 圖片與文案")

col1, col2 = st.columns(2)
with col1:
    bg_img = image_input_area("背景圖", "bg")
    p1_img = image_input_area("商品圖 A", "p1")
    p2_img = image_input_area("商品圖 B", "p2")

with col2:
    st.write("---")
    st.info("""
    * **背景圖尺寸為 888 × 1020 px**
    * 可上傳兩張商品圖，圖片自動去背
    * 可自訂標題及按鈕文字
    * 按鈕可自動偵測背景選色
    """)
    
    text_line1 = st.text_input("主標題", "NIKE × 愛迪達")
    text_line2 = st.text_input("副標題", "結帳享84折")
    btn_text = st.text_input("按鈕文字", "立即前往")

if st.button("生成圖片"):
    if not font_upload:
        st.error("❌ 請先在左側選單上傳「字型檔案」！")
    elif bg_img and p1_img and p2_img:
        try:
            final, detected_color = create_composite_image(bg_img, p1_img, p2_img, text_line1, text_line2, btn_text, font_upload)
            
            st.success(f"生成完成！使用色碼: {detected_color}")
            st.image(final, caption="預覽", use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="PNG")
            st.download_button("下載圖片", buf.getvalue(), "banner.png", "image/png")
        except Exception as e:
            st.error(f"發生錯誤: {e}")
    else:
        st.warning("請確保背景圖與兩張商品圖皆已準備好。")
