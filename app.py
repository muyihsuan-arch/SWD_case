import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib # 新增：用於產生唯一識別碼
import time

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
TIMEOUT_SECONDS = 43200  # 12 小時

# === 2. 核心技術：處理預覽與唯一 Key ===
@st.cache_data(ttl=600)
def get_audio_base64(url):
    if not isinstance(url, str) or url == "": return None
    # 自動處理 SharePoint 轉址下載
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
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

def generate_id(link):
    """利用連結網址產生唯一的 10 位數代碼，不受資料排序影響"""
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

# === 3. CSS 樣式與頁面設定 ===
st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

st.markdown("""
    <style>
        .stButton button { border-radius: 20px; font-weight: bold; }
        .category-tag { background-color: #f1f3f4; color: #5f6368; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
        /* 隱藏預設播放器下載按鈕 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# === 4. 資料載入 (強化魯棒性) ===
@st.cache_data(ttl=300) # 縮短為 5 分鐘，以對應資料定時更新的需求
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 確保必要欄位存在
        for col in ['title', 'link', 'category', 'type']:
            if col not in df.columns: df[col] = ""
        
        df = df.fillna("")
        # 排除邏輯
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        df = df[~df['title'].astype(str).str.lower().str.endswith(img_ext)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"表格載入失敗: {e}")
        return pd.DataFrame()

# === 5. 複製功能 ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee;">
        <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin-bottom: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button onclick="copyToClipboard()" style="width: 100%; padding: 8px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📋 複製連結</button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                navigator.clipboard.writeText(copyText.value).then(function() {{ alert("✅ 複製成功！"); }});
            }}
        </script>
    </div>
    """
    components.html(html_code, height=120)

# === 6. 主程式 ===
def main():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login"):
            pw = st.text_input("輸入密碼解鎖", type="password")
            if st.form_submit_button("解鎖資料庫", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("⚠️ 密碼錯誤")
        return

    df = load_data()
    if df.empty: return

    # 搜尋與篩選介面
    search_query = st.text_input("🔍 搜尋品牌、產品關鍵字", placeholder="例如：房屋")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📁 選擇分類", ["全部"] + cat_list)
    with col2:
        type_filter = st.radio("📑 媒體類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 過濾邏輯
    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        keys = search_query.lower().split()
        search_target = df['title'].astype(str) + " " + df['category'].astype(str) + " " + df['type'].astype(str)
        mask &= search_target.str.lower().apply(lambda x: any(k in x for k in keys))
    if sel_cat != "全部":
        mask &= (df['category'].astype(str) == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].astype(str).str.contains(type_filter, case=False) | df['title'].astype(str).str.contains(type_filter, case=False))

    results = df[mask]
    st.caption(f"🎯 找到 {len(results)} 筆結果")

    # 列表渲染
    for _, row in results.iterrows():
        # 為每一筆資料產生基於 Link 的唯一 ID
        uid = generate_id(row['link'])
        
        with st.expander(f"📄 {row['title']}"):
            st.markdown(f"<span class='category-tag'>{row['category']}</span><span class='category-tag'>{row['type']}</span>", unsafe_allow_html=True)
            
            t_low = str(row['title']).lower()
            tp_low = str(row['type']).lower()
            
            # 音訊預覽
            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                if st.button("▶️ 載入音訊", key=f"play_{uid}"):
                    with st.spinner("載入中..."):
                        b64 = get_audio_base64(row['link'])
                        if b64: st.audio(b64)
                        else: st.error("載入失敗")
            # 影片/文件預覽
            else:
                st.components.v1.iframe(get_embed_url(row['link']), height=400)

            c1, c2 = st.columns(2)
            with c1:
                st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with c2:
                if st.button("🔗 複製連結", key=f"copy_{uid}", use_container_width=True):
                    render_copy_ui(row['link'])

if __name__ == "__main__":
    main()
