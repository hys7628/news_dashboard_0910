import os
import io
import re
import streamlit as st
from docx import Document
from docx.oxml.ns import qn
from PIL import Image

# 1. 기본 페이지 레이아웃 설정
st.set_page_config(page_title="주요 뉴스", layout="wide")
st.title("📰 주요 뉴스")

# 2. 신문 스크랩 워드 파일 고정 경로 (절대 수정 금지)
BASE_DIR = "/Users/han-yunsu/Desktop/신문 스크랩/2026"

# OpenXML 네임스페이스 매핑
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
}

# 3. 워드 파일에서 텍스트 및 [워드 회전 각도가 반영된 이미지] 추출 함수
def load_docx_content(file_path):
    doc = Document(file_path)
    
    # 공백이 아닌 본문 문단 추출
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    # 워드 XML에서 이미지 회전 각도(rot) 추출
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
            
            # 오타 수정: xfrm_elements
            if xfrm_elements and 'rot' in xfrm_elements[0].attrib:
                rot_val = int(xfrm_elements[0].attrib['rot']) // 60000
                rotations[embed_id] = rot_val
            else:
                rotations[embed_id] = 0
    except Exception:
        pass

    # 워드 문서 내부 이미지 추출 및 회전 보정
    images = []
    for rel_id, rel in doc.part.rels.items():
        if "image" in rel.target_ref:
            img_bytes = rel.target_part.blob
            img = Image.open(io.BytesIO(img_bytes))
            
            deg = rotations.get(rel_id, 0)
            if deg != 0:
                img = img.rotate(-deg, expand=True)
                
            images.append(img)
            
    return paragraphs, images

# 4. 파일명 앞의 대괄호([])에서 산업군 추출 및 파일 분류 함수
def get_files_by_category(base_dir):
    """
    고정 경로('/Users/han-yunsu/Desktop/신문 스크랩/2026') 내 모든 하위 폴더 탐색
    { "산업군": { "표시용_파일명": "전체_절대경로" } }
    """
    categorized_files = {}

    for root, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(".docx") and not filename.startswith("~$"):
                full_path = os.path.join(root, filename)
                
                # 파일명에서 첫 번째 [대괄호] 내부 텍스트 추출 (예: [경제] -> 경제)
                match = re.search(r'\[(.*?)\]', filename)
                if match:
                    category = match.group(1).strip()
                else:
                    category = "기타"
                
                if category not in categorized_files:
                    categorized_files[category] = {}
                
                # 사이드바에 파일명이 중복되어도 구분되도록 상대경로를 보존하되 표시용 이름 매핑
                relative_path = os.path.relpath(full_path, base_dir)
                categorized_files[category][relative_path] = full_path

    return categorized_files

# 5. 메인 레이아웃 및 사이드바 로직
left_col, center_col, right_col = st.columns([0.1, 0.8, 0.1])

with center_col:
    if not os.path.exists(BASE_DIR):
        st.error(f"지정된 경로를 찾을 수 없습니다: {BASE_DIR}")
    else:
        categorized_data = get_files_by_category(BASE_DIR)
        
        if not categorized_data:
            st.warning(f"'{BASE_DIR}' 경로 및 하위 폴더에 읽을 수 있는 워드(.docx) 파일이 없습니다.")
        else:
            # 사이드바: 산업군 분류
            st.sidebar.title("산업군 분류")
            category_list = sorted(list(categorized_data.keys()))
            selected_category = st.sidebar.selectbox("산업군을 선택하세요:", category_list)
            
            # 선택된 산업군에 속한 파일 선택
            files_in_category = categorized_data[selected_category]
            selected_display_name = st.sidebar.selectbox(
                "기사 파일 선택:", 
                list(files_in_category.keys()),
                format_func=lambda x: os.path.basename(x)  # 드롭다운에는 깔끔하게 파일명만 노출
            )
            selected_file_path = files_in_category[selected_display_name]
            
            try:
                paragraphs, images = load_docx_content(selected_file_path)
                
                # '제목:' 또는 '제목 :'으로 시작하는 문장 분리
                header_text = None
                remaining_paragraphs = []
                
                for p in paragraphs:
                    if (p.startswith("제목 :") or p.startswith("제목:")) and header_text is None:
                        cleaned_header = p.replace("제목 :", "").replace("제목:", "").strip()
                        header_text = cleaned_header
                    else:
                        remaining_paragraphs.append(p)
                
                if not header_text:
                    base_name = os.path.basename(selected_file_path).replace(".docx", "")
                    header_text = re.sub(r'\[.*?\]', '', base_name).strip()

                # 1. 사진 바로 위: st.header 적용
                st.header(header_text)
                
                # 2. 첨부된 사진 (워드 회전값 보정 적용)
                if images:
                    st.image(images[0], use_container_width=True)
                else:
                    st.info("워드 파일 내에 삽입된 사진이 없습니다.")
                
                st.markdown("---")
                
                # 3. 사진 바로 밑: 나머지 요약 내용
                for paragraph in remaining_paragraphs:
                    st.write(paragraph)
                    
            except Exception as e:
                st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")