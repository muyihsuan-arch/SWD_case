import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import time

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
TIMEOUT_SECONDS = 43200  # 12 小時

# === 2. 核心技術：處理預覽功能 ===
@st.cache_data(ttl=600)
def get_audio_base64(url):
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
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. CSS 樣式與頁面設定 ===
st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")

st.markdown("""
    <style>
        .stButton button { border-radius: 20px; font-weight: bold; }
        .category-tag { background-color: #f1f3f4; color: #5f6368; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
    </style>
""", unsafe_allow_html=True)

# === 4. 資料載入 (徹底修復 KeyError 與屬性錯誤) ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        # 強制將所有標頭去除空格、轉小寫
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 確保必要欄位存在，若原本是大寫 Link，現在會變成 link
        required = ['title', 'link', 'category', 'type']
        for col in required:
            if col not in df.columns:
                # 建立空欄位防止程式崩潰
                df[col] = ""
        
        # 修正：加上 .astype(str) 與 .str 確保不會報 endswith 錯誤
        df = df[df['title'].notna() & df['link'].notna()]
        img_ext = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        
        # 關鍵修正：確保檢查的是字串
        is_not_img = ~df['title'].astype(str).str.lower().str.endswith(img_ext)
        is_not_folder = ~df['link'].astype(str).str.contains('/folders/')
        
        return df[is_not_img & is_not_folder]
    except Exception as e:
        st.error(f"資料載入失敗: {e}")
        return pd.DataFrame()

# === 5. 複製功能 ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #eee;">
        <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 8px; margin-bottom: 8px;">
        <button onclick="copyToClipboard()" style="width: 100%; padding: 8px; background: #0097DA; color: white; border: none; border-radius: 5px; cursor: pointer;">📋 複製連結</button>
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
    
    # 登入邏輯
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

    df = load_data()
    if df.empty:
        st.warning("資料庫目前沒有資料。")
        return

    # 搜尋與篩選 (統一使用小寫 Key)
    search_query = st.text_input("🔍 搜尋品牌、產品關鍵字", placeholder="例如：房屋")
    
    col1, col2 = st.columns(2)
    with col1:
        cat_list = sorted([str(x) for x in df['category'].unique() if x])
        categories = ["全部"] + cat_list
        sel_cat = st.selectbox("📂 選擇分類", categories)
    with col2:
        type_filter = st.radio("🎞️ 媒體類型", ["全部", "企頻", "新鮮視", "側帶"], horizontal=True)

    # 過濾邏輯
    mask = pd.Series([True] * len(df))
    if search_query:
        keys = search_query.lower().split()
        mask &= df.apply(lambda r: any(k in f"{r['title']} {r['category']} {r['type']}".lower() for k in keys), axis=1)
    if sel_cat != "全部":
        mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        t_mask = df['type'].astype(str).str.contains(type_filter, case=False, na=False) | \
                 df['title'].astype(str).str.contains(type_filter, case=False, na=False)
        mask &= t_mask

    results = df[mask]
    st.caption(f"找到 {len(results)} 筆結果")

    for _, row in results.iterrows():
        with st.expander(f"📄 {row['title']}"):
            st.markdown(f"<span class='category-tag'>{row['category']}</span><span class='category-tag'>{row['type']}</span>", unsafe_allow_html=True)
            
            t_low = str(row['title']).lower()
            tp_low = str(row['type']).lower()
            
            # 音訊判定
            if any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low:
                if st.button("▶️ 載入音訊", key=f"a_{row['title']}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
                    else: st.error("載入失敗")
            else:
                st.components.v1.iframe(get_embed_url(row['link']), height=400)

            c1, c2 = st.columns(2)
            with c1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with c2:
                if st.button("🔗 複製連結", key=f"c_{row['title']}", use_container_width=True):
                    render_copy_ui(row['link'])

if __name__ == "__main__":
    main()
