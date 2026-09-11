import os
import base64
import io
import re
import unicodedata
import streamlit as st
from docx import Document
from docx.oxml.ns import qn
from PIL import Image

# 1. 기본 페이지 레이아웃 설정
st.set_page_config(page_title="News Hub", layout="wide", initial_sidebar_state="collapsed")

# 2. os.path.join 기반 동적 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = CURRENT_DIR if os.path.basename(CURRENT_DIR) == "news_dashboard" else os.path.join(CURRENT_DIR, "news_dashboard")
if not os.path.exists(ROOT_DIR):
    ROOT_DIR = CURRENT_DIR

# 음원 경로
AUDIO_PATH = os.path.join(ROOT_DIR, "news.mp3")

# 우측 일러스트 경로 (news_dashboard 루트 폴더)
ASSET_DIR = ROOT_DIR

# 좌측 이모티콘 아이콘 경로 (news_dashboard/CATEGORY_EMOJI_PNG)
ICON_DIR = os.path.join(ROOT_DIR, "CATEGORY_EMOJI_PNG")

# 워드 파일 경로 (news_scrapping 또는 신문 스크랩 자동 매칭)
BASE_DIR = os.path.join(ROOT_DIR, "news_scrapping")
if not os.path.exists(BASE_DIR):
    candidate_kr = os.path.join(ROOT_DIR, "신문 스크랩")
    if os.path.exists(candidate_kr):
        BASE_DIR = candidate_kr

# 한글 및 영문 카테고리 통합 매핑 (좌측 아이콘 / 우측 일러스트)
CATEGORY_META = {
    # 반도체
    "반도체": {"icon": "반도체.png", "image": "Semiconductor.png"},
    "semiconductor": {"icon": "반도체.png", "image": "Semiconductor.png"},
    # 경제
    "경제": {"icon": "경제.png", "image": "Economy.png"},
    "economy": {"icon": "경제.png", "image": "Economy.png"},
    # 금융
    "금융": {"icon": "금융.png", "image": "Finance.png"},
    "finance": {"icon": "금융.png", "image": "Finance.png"},
    # 석유
    "석유": {"icon": "석유.png", "image": "Oil.png"},
    "oil": {"icon": "석유.png", "image": "Oil.png"},
    # 에너지
    "에너지": {"icon": "에너지.png", "image": "Energy.png"},
    "energy": {"icon": "에너지.png", "image": "Energy.png"},
    # 기타 및 추가 산업군
    "기타": {"icon": "기타.png", "image": ""},
    "other": {"icon": "기타.png", "image": ""},
    "it": {"icon": "IT.png", "image": ""},
    "테크": {"icon": "테크.png", "image": ""},
    "모빌리티": {"icon": "모빌리티.png", "image": ""},
    "바이오": {"icon": "바이오.png", "image": ""},
    "부동산": {"icon": "부동산.png", "image": ""},
    "글로벌": {"icon": "글로벌.png", "image": ""},
    "산업": {"icon": "산업.png", "image": ""}
}

def resolve_category_meta(category_name):
    clean_cat = unicodedata.normalize('NFC', str(category_name).strip().lower())
    if clean_cat in CATEGORY_META:
        return CATEGORY_META[clean_cat]
    for key, val in CATEGORY_META.items():
        if key in clean_cat:
            return val
    return CATEGORY_META["기타"]

# 이미지 파일 Base64 변환 함수 (우측 일러스트)
def get_image_base64(file_name):
    if not file_name:
        return ""
    img_path = os.path.join(ASSET_DIR, file_name)
    if os.path.exists(img_path):
        try:
            with open(img_path, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception:
            return ""
    # 대소문자 차이 보정 탐색
    if os.path.exists(ASSET_DIR):
        target_lower = file_name.lower()
        for f in os.listdir(ASSET_DIR):
            if f.lower() == target_lower:
                try:
                    with open(os.path.join(ASSET_DIR, f), "rb") as fp:
                        return f"data:image/png;base64,{base64.b64encode(fp.read()).decode()}"
                except Exception:
                    pass
    return ""

# 좌측 이모티콘 아이콘 Base64 변환 함수 (NFC 한글 정규화 적용)
def get_icon_base64(file_name):
    if not file_name or not os.path.exists(ICON_DIR):
        return ""
    file_name_nfc = unicodedata.normalize('NFC', file_name)
    for actual_file in os.listdir(ICON_DIR):
        if unicodedata.normalize('NFC', actual_file) == file_name_nfc:
            try:
                with open(os.path.join(ICON_DIR, actual_file), "rb") as f:
                    return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
            except Exception:
                pass
    return ""

# 배경음악 제어 함수
def play_background_audio(audio_file_path, volume=0.1):
    if os.path.exists(audio_file_path):
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        encoded_audio = base64.b64encode(audio_bytes).decode()
        
        audio_html = f"""
            <audio id="bg-audio" autoplay loop style="display:none;">
                <source src="data:audio/mp3;base64,{encoded_audio}" type="audio/mp3">
            </audio>
            <script>
                var audio = document.getElementById("bg-audio");
                if (audio) {{
                    audio.volume = {volume};
                    audio.play().catch(function(error) {{
                        document.addEventListener('click', function() {{
                            audio.volume = {volume};
                            audio.play();
                        }}, {{ once: true }});
                    }});
                }}
            </script>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

# 3. 반응형 디자인 스타일링
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        box-sizing: border-box !important;
    }

    .stApp {
        background-color: #dbe4f0 !important;
        background-image: 
            radial-gradient(at 10% 15%, rgba(197, 215, 255, 0.85) 0px, transparent 55%),
            radial-gradient(at 90% 10%, rgba(224, 205, 255, 0.75) 0px, transparent 50%),
            radial-gradient(at 5% 85%, rgba(209, 245, 235, 0.85) 0px, transparent 55%),
            radial-gradient(at 95% 85%, rgba(255, 226, 209, 0.8) 0px, transparent 50%),
            radial-gradient(at 50% 50%, rgba(238, 242, 250, 0.6) 0px, transparent 65%) !important;
        background-attachment: fixed !important;
        background-size: cover !important;
    }

    .main .block-container {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(35px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(35px) saturate(180%) !important;
        border-radius: clamp(20px, 4vw, 36px) !important;
        border: 1.5px solid rgba(255, 255, 255, 0.85) !important;
        box-shadow: 0 25px 60px rgba(80, 100, 140, 0.12),
                    inset 0 1px 2px rgba(255, 255, 255, 0.9) !important;
        padding: clamp(20px, 4vw, 44px) !important;
        margin-top: clamp(10px, 2.5vw, 25px) !important;
        margin-bottom: clamp(15px, 3vw, 35px) !important;
        max-width: 1240px !important;
        width: 95% !important;
    }

    @keyframes floating {
        0% { transform: translateY(0px) scale(1); box-shadow: 0 15px 35px rgba(50, 80, 150, 0.18); }
        50% { transform: translateY(-14px) scale(1.02); box-shadow: 0 25px 45px rgba(50, 80, 150, 0.28); }
        100% { transform: translateY(0px) scale(1); box-shadow: 0 15px 35px rgba(50, 80, 150, 0.18); }
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        width: clamp(140px, 22vw, 185px) !important;
        height: clamp(140px, 22vw, 185px) !important;
        border-radius: 50% !important;
        background: radial-gradient(circle at 32% 32%, #ffffff 0%, #dbeafe 65%, #93c5fd 100%) !important;
        border: 3px solid rgba(255, 255, 255, 0.95) !important;
        color: #1e3a8a !important;
        letter-spacing: 1.5px !important;
        animation: floating 3.2s ease-in-out infinite !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
        cursor: pointer !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    
    div[data-testid="stButton"] > button[kind="primary"] * {
        font-size: clamp(2.3rem, 4.5vw, 3.3rem) !important;
        font-weight: 800 !important;
        line-height: 1 !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        transform: scale(1.06) !important;
        box-shadow: 0 25px 50px rgba(37, 99, 235, 0.35) !important;
        border-color: #60a5fa !important;
        color: #1d4ed8 !important;
    }

    @keyframes morphSplit {
        0% { opacity: 0; transform: scale(0.2) translateY(-40px); border-radius: 50%; }
        60% { opacity: 0.9; border-radius: 35px; }
        100% { opacity: 1; transform: scale(1) translateY(0px); border-radius: 26px; }
    }

    .industry-card {
        background: rgba(255, 255, 255, 0.92) !important;
        border-radius: 24px !important;
        padding: clamp(16px, 2.2vw, 24px) !important;
        box-shadow: 0 12px 30px rgba(100, 125, 160, 0.07),
                    inset 0 1px 1px rgba(255, 255, 255, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.95) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        margin-bottom: 12px !important;
        min-height: clamp(140px, 18vw, 160px) !important;
        animation: morphSplit 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) backwards !important;
    }

    .industry-card:hover {
        transform: translateY(-5px) scale(1.015) !important;
        background: #ffffff !important;
        box-shadow: 0 20px 40px rgba(70, 95, 140, 0.13) !important;
        border-color: #ffffff !important;
    }

    .card-content-wrapper {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
        gap: 10px !important;
    }

    .card-left-info {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    .card-left-icon-img {
        width: clamp(28px, 3.5vw, 36px) !important;
        height: clamp(28px, 3.5vw, 36px) !important;
        object-fit: contain !important;
        margin-bottom: 8px !important;
        display: block !important;
    }

    .card-right-thumb {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex: 0 0 auto !important;
    }

    .card-right-img {
        width: clamp(65px, 8vw, 85px) !important;
        height: clamp(65px, 8vw, 85px) !important;
        object-fit: contain !important;
        display: block !important;
        filter: drop-shadow(0 8px 14px rgba(50, 70, 110, 0.12)) !important;
    }

    .industry-card.delay-0 { animation-delay: 0.05s; }
    .industry-card.delay-1 { animation-delay: 0.12s; }
    .industry-card.delay-2 { animation-delay: 0.19s; }
    .industry-card.delay-3 { animation-delay: 0.26s; }
    .industry-card.delay-4 { animation-delay: 0.33s; }
    .industry-card.delay-5 { animation-delay: 0.40s; }

    .card-title {
        font-size: clamp(1.1rem, 1.6vw, 1.3rem) !important;
        font-weight: 800 !important;
        color: #111827 !important;
        margin-bottom: 5px !important;
        letter-spacing: -0.3px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    .card-badge {
        display: inline-block !important;
        font-size: clamp(0.7rem, 1vw, 0.78rem) !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        border-radius: 20px !important;
        background: #f1f5f9 !important;
        color: #475569 !important;
        white-space: nowrap !important;
    }

    div[data-testid="stButton"] > button:not([kind="primary"]) {
        border-radius: 20px !important;
        border: 1px solid rgba(203, 213, 225, 0.8) !important;
        background: #ffffff !important;
        color: #334155 !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        transition: all 0.2s ease !important;
        font-size: clamp(0.85rem, 1.1vw, 0.95rem) !important;
    }

    div[data-testid="stButton"] > button:not([kind="primary"]):hover {
        background: #0f172a !important;
        color: #ffffff !important;
        border-color: #0f172a !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18) !important;
    }

    @media (max-width: 768px) {
        .main .block-container {
            width: 98% !important;
            padding: 18px 16px !important;
            border-radius: 22px !important;
        }
        .card-content-wrapper {
            gap: 6px !important;
        }
        .card-right-img {
            width: 60px !important;
            height: 60px !important;
        }
        .card-left-icon-img {
            width: 28px !important;
            height: 28px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# 4. 세션 상태 관리
if "is_expanded" not in st.session_state:
    st.session_state.is_expanded = False
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

# 5. 워드 파일 파싱 함수 (회전 각도 보정)
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
}

def load_docx_content(file_path):
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    rotations = {}
    try:
        blips = doc.element.xpath('//a:blip', namespaces=NAMESPACES)
        for blip in blips:
            embed_id = blip.attrib.get(qn('r:embed'))
            if not embed_id:
                continue
            xfrm_elements = (
                blip.xpath('./ancestor::pic:pic//a:xfrm', namespaces=NAMESPACES) or
                blip.xpath('./ancestor::wp:inline//a:xfrm', namespaces=NAMESPACES) or
                blip.xpath('./ancestor::wp:anchor//a:xfrm', namespaces=NAMESPACES)
            )
            if xfrm_elements and 'rot' in xfrm_elements[0].attrib:
                rotations[embed_id] = int(xfrm_elements[0].attrib['rot']) // 60000
            else:
                rotations[embed_id] = 0
    except Exception:
        pass

    images = []
    for rel_id, rel in doc.part.rels.items():
        if "image" in rel.target_ref:
            img = Image.open(io.BytesIO(rel.target_part.blob))
            deg = rotations.get(rel_id, 0)
            if deg != 0:
                img = img.rotate(-deg, expand=True)
            images.append(img)
            
    return paragraphs, images

# 6. 연도/월별 하위 폴더 재귀 탐색
def get_categorized_files(base_dir):
    data = {}
    if not base_dir or not os.path.exists(base_dir):
        return data

    for root, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(".docx") and not filename.startswith("~$"):
                full_path = os.path.join(root, filename)
                match = re.search(r'\[(.*?)\]', filename)
                if match:
                    raw_cat = match.group(1).strip()
                    category = unicodedata.normalize('NFC', raw_cat)
                else:
                    category = "기타"
                
                if category not in data:
                    data[category] = []
                data[category].append(full_path)
    return data

categorized_data = get_categorized_files(BASE_DIR)

# -------------------------------------------------------------
# STEP 1 : 물방울 인트로 화면
# -------------------------------------------------------------
if not st.session_state.is_expanded:
    play_background_audio(AUDIO_PATH, volume=0.1)

    st.write("<div style='height: clamp(15vh, 22vh, 25vh);'></div>", unsafe_allow_html=True)
    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        if st.button("News", type="primary", use_container_width=True):
            st.session_state.is_expanded = True
            st.rerun()

# -------------------------------------------------------------
# STEP 2 & 3 : 산업군 직사각형 카드 그리드 화면
# -------------------------------------------------------------
else:
    top_col1, top_col2 = st.columns([7.5, 2.5])
    with top_col1:
        st.subheader("📰 산업별 주요 뉴스 대시보드")
    with top_col2:
        if st.button("🔄 Home", use_container_width=True):
            st.session_state.is_expanded = False
            st.session_state.selected_category = None
            st.session_state.selected_file = None
            st.rerun()

    if not categorized_data:
        target_display = BASE_DIR if BASE_DIR else "지정된 경로"
        st.warning(f"'{target_display}' 경로 및 하위 연도/월 폴더에 워드 파일이 없습니다.")
    else:
        categories = list(categorized_data.keys())
        cols = st.columns(3)
        for idx, category in enumerate(categories):
            col = cols[idx % 3]
            with col:
                norm_cat = unicodedata.normalize('NFC', category)
                file_count = len(categorized_data[category])
                
                # 한글/영문 모두 대응하는 메타데이터 조회
                meta = resolve_category_meta(norm_cat)

                # 1. 좌측 이모티콘 PNG
                icon_data_uri = get_icon_base64(meta["icon"])
                icon_html = f'<img src="{icon_data_uri}" class="card-left-icon-img" alt="{norm_cat}">' if icon_data_uri else '<div class="card-left-icon-img"></div>'

                # 2. 우측 일러스트 PNG
                right_img_uri = get_image_base64(meta["image"])
                right_img_html = f'<img src="{right_img_uri}" class="card-right-img" alt="{norm_cat}">' if right_img_uri else '<div class="card-right-img"></div>'

                st.markdown(f"""
                <div class="industry-card delay-{idx % 6}">
                    <div class="card-content-wrapper">
                        <div class="card-left-info">
                            {icon_html}
                            <div class="card-title">{category}</div>
                            <span class="card-badge">등록된 기사 {file_count}편</span>
                        </div>
                        <div class="card-right-thumb">
                            {right_img_html}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"{category} 기사 보기 ➔", key=f"cat_btn_{category}", use_container_width=True):
                    st.session_state.selected_category = category
                    st.session_state.selected_file = None
                    st.rerun()

        # -------------------------------------------------------------
        # STEP 5 : 기사 목록 & 본문 내용 출력
        # -------------------------------------------------------------
        if st.session_state.selected_category:
            current_cat = st.session_state.selected_category
            files = categorized_data[current_cat]

            st.markdown("---")
            st.markdown(f"### 📰 **[{current_cat}]** 관련 기사 목록")

            file_options = {os.path.basename(f): f for f in files}
            selected_filename = st.selectbox(
                "확인할 기사를 선택하세요:",
                list(file_options.keys()),
                key="article_selector"
            )

            if selected_filename:
                target_path = file_options[selected_filename]
                try:
                    paragraphs, images = load_docx_content(target_path)
                    
                    header_text = None
                    body_paragraphs = []
                    for p in paragraphs:
                        if (p.startswith("제목 :") or p.startswith("제목:")) and header_text is None:
                            header_text = p.replace("제목 :", "").replace("제목:", "").strip()
                        else:
                            body_paragraphs.append(p)
                    
                    if not header_text:
                        clean_name = os.path.basename(target_path).replace(".docx", "")
                        header_text = re.sub(r'\[.*?\]', '', clean_name).strip()

                    _, viewer_col, _ = st.columns([0.02, 0.96, 0.02])
                    with viewer_col:
                        st.header(header_text)
                        
                        if images:
                            st.image(images[0], use_container_width=True)
                        else:
                            st.info("첨부된 이미지가 없습니다.")
                        
                        st.markdown("---")
                        for p in body_paragraphs:
                            st.write(p)
                            
                except Exception as e:
                    st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")