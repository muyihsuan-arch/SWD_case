import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import time

# === 1. 設定區 ===
# 這裡換成你 HTML 裡面的 CSV 網址
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
TIMEOUT_SECONDS = 43200  # 12 小時 (比照 HTML 版 SESSION_HOURS = 12)

# === 2. 核心技術：處理預覽功能 ===
@st.cache_data(ttl=600)
def get_audio_base64(url):
    """處理音訊 Base64，解決部分瀏覽器無法直接播放 OneDrive 連結的問題"""
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except: return None
    return None

def get_embed_url(link):
    """將 Google Drive 連結轉為預覽連結"""
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. CSS 樣式美化 (融合全家藍色調) ===
st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

st.markdown("""
    <style>
        :root { --primary: #0097DA; }
        .stButton button { border-radius: 20px; font-weight: bold; }
        .stTextInput input { border-radius: 10px; }
        /* 隱藏預設播放器的下載按鈕 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        .category-tag { 
            background-color: #f1f3f4; 
            color: #5f6368; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 12px; 
            margin-right: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# === 4. 複製功能組件 ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee;">
        <input type="text" value="{text_to_copy}" id="copyInput" readonly 
            style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 8px;">
        <button onclick="copyToClipboard()" 
            style="width: 100%; padding: 8px; background-color: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer;">
            📋 複製連結
        </button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                navigator.clipboard.writeText(copyText.value).then(function() {{
                    alert("✅ 複製成功！");
                }});
            }}
        </script>
    </div>
    """
    components.html(html_code, height=120)

# === 5. 資料載入與過濾邏輯 ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        # 排除邏輯 (比照 HTML 版)
        # 1. 排除標題與分類相同的行 (通常是重複標籤)
        # 2. 排除資料夾連結
        # 3. 排除純圖片
        df = df[df['Title'].notna() & df['Link'].notna()]
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['Title'].str.lower().endswith(img_ext)]
        df = df[~df['Link'].str.contains('/folders/')]
        return df
    except:
        return pd.DataFrame()

# === 6. 主程式 ===
def main():
    # 登入邏輯
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        if time.time() - st.session_state.login_time > TIMEOUT_SECONDS:
            st.session_state.logged_in = False
            st.rerun()

    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login"):
            pw = st.text_input("輸入密碼解鎖", type="password")
            if st.form_submit_button("解鎖資料庫", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.login_time = time.time()
                    st.rerun()
                else: st.error("⚠️ 密碼錯誤")
        return

    # 介面開始
    df = load_data()
    
    # 搜尋與篩選區
    search_query = st.text_input("🔍 搜尋品牌、產品關鍵字", placeholder="例如：葉黃素")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        categories = ["ALL"] + sorted(df['Category'].dropna().unique().tolist())
        sel_cat = st.selectbox("📂 選擇分類", categories)
    with col2:
        # 模擬 HTML 版的橫向按鈕，這裡用 Tabs 或 Segmented Control
        type_filter = st.radio("🎞️ 媒體類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 過濾邏輯 (完全比照 HTML 原文邏輯)
    mask = pd.Series([True] * len(df))
    
    if search_query:
        # 支援多關鍵字搜尋
        keys = search_query.lower().split()
        mask &= df.apply(lambda r: any(k in f"{r['Title']} {r['Category']} {r['Type']}".lower() for k in keys), axis=1)
    
    if sel_cat != "ALL":
        mask &= (df['Category'] == sel_cat)
        
    if type_filter != "全部":
        if type_filter == "企頻":
            mask &= (df['Type'].str.contains("企頻|radio", case=False, na=False) | df['Title'].str.contains(".mp3|.wav", case=False, na=False))
        elif type_filter == "新鮮視":
            mask &= (df['Type'].str.contains("新鮮視|vision", case=False, na=False) | df['Title'].str.contains(".mp4|.mov", case=False, na=False))
        elif type_filter == "側帶":
            mask &= (df['Type'].str.contains("側帶", na=False) | df['Title'].str.contains("側帶", na=False))

    results = df[mask]

    st.caption(f"找到 {len(results)} 筆結果")
    st.divider()

    # 列表渲染
    for _, row in results.iterrows():
        with st.expander(f"📄 {row['Title']}"):
            st.markdown(f"<span class='category-tag'>{row['Category']}</span> <span class='category-tag'>{row['Type']}</span>", unsafe_allow_html=True)
            
            # 判斷媒體類型並顯示預覽
            title_lower = str(row['Title']).lower()
            type_lower = str(row['Type']).lower()
            
            # A. 音訊預覽
            if any(ext in title_lower for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in type_lower or "radio" in type_lower:
                if st.button("▶️ 載入音訊", key=f"btn_{row['Title']}"):
                    b64 = get_audio_base64(row['Link'])
                    if b64: st.audio(b64)
                    else: st.error("音訊載入失敗")
            
            # B. 影片/文件預覽 (iframe)
            else:
                embed_url = get_embed_url(row['Link'])
                st.components.v1.iframe(embed_url, height=400)

            # 功能按鈕
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("↗ 開啟檔案", row['Link'], use_container_width=True)
            with c2:
                # 點擊後開啟複製 UI
                if st.button("🔗 複製連結", key=f"cp_{row['Title']}", use_container_width=True):
                    render_copy_ui(row['Link'])

if __name__ == "__main__":
    main()
