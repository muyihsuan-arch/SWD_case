import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
PASSWORD = "888"
# 部署後請務必修改此網址為您的實際網址
SITE_URL = "https://swd-case.streamlit.app" 

# === 2. 核心技術函數 ===
def generate_id(link):
    """利用網址連結產生唯一的 10 位數代碼，不受 CSV 排序變動影響"""
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

@st.cache_data(ttl=120)
def get_audio_base64(url):
    """處理 SharePoint 音訊轉碼，並設定 2 分鐘快取釋放記憶體壓力"""
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except: return None
    return None

def get_embed_url(link):
    """轉換 Google Drive / SharePoint 預覽連結"""
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. 資料載入與過濾核心 ===
@st.cache_data(ttl=180)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 確保必要欄位存在，包含新增的 short 欄位
        for col in ['title', 'link', 'category', 'type', 'short']:
            if col not in df.columns: df[col] = ""
        
        df = df.fillna("")
        
        # 顯示邏輯：若 Short 欄位為空，則以 Title 補上
        df['short'] = df.apply(lambda r: r['short'] if str(r['short']).strip() != "" else r['title'], axis=1)
        
        # 過濾邏輯：排除「案例資料庫」與純資料夾連結
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except:
        return pd.DataFrame()

# === 4. UI 元件：分享與複製介面 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
    """處理複製連結按鈕與版權保護警告文字"""
    if is_disabled:
        html_code = f"""
        <div style="background-color:#fff5f5;padding:12px;border-radius:8px;border:1px solid #feb2b2;margin-bottom:10px;">
            <label style="font-size:12px;color:#c53030;font-weight:bold;">{label}</label>
            <p style="font-size:13px;color:#333;margin:8px 0;line-height:1.4;">⚠️ {warning_msg}</p>
        </div>
        """
    else:
        html_code = f"""
        <div style="background-color:#f8f9fa;padding:10px;border-radius:8px;border:1px solid #eee;margin-bottom:10px;">
            <label style="font-size:12px;color:#666;">{label}</label>
            <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width:100%;padding:8px;margin:5px 0;border:1px solid #ddd;border-radius:4px;">
            <button onclick="copyToClipboard()" style="width:100%;padding:10px;background:#0097DA;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">📋 點此複製網址</button>
            <script>
                function copyToClipboard() {{
                    var copyText = document.getElementById("copyInput");
                    copyText.select();
                    navigator.clipboard.writeText(copyText.value).then(function() {{ alert("✅ 複製成功！"); }});
                }}
            </script>
        </div>
        """
    components.html(html_code, height=150)

@st.dialog("🔗 分享檔案權限")
def show_share_dialog(display_name, link, uid, is_video=False, is_image=False):
    st.write(f"📄 **{display_name}**")
    render_copy_ui("🏢 內部分享連結 (同仁下載用)", link)
    if is_video:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, warning_msg="影片涉及『客戶版權』及『全家便利商店場域』，不提供對外分享。")
    elif is_image:
        render_copy_ui("🌏 外部分享連結", "", is_disabled=True, warning_msg="此為『圖片檔』，涉及版權保護，不提供對外分享。")
    else:
        share_link = f"{SITE_URL}?id={uid}"
        render_copy_ui("🌏 外部分享連結 (客戶試聽/防下載)", share_link)

# === 5. 主程式架構 ===
def main():
    # 5.1 頁面基本配置 (必須在最上方)
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    # 5.2 初始化 Session 狀態
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20

    df = load_data()
    if df.empty:
        st.error("目前無法連線至資料庫，請稍後再試。")
        return

    # 5.3 優先判定：網址參數 (客戶模式不需要登入)
    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            t_low = str(item['title']).lower()
            tp_low = str(item['type']).lower()
            
            # 客戶端安全檢查：禁止預覽影片與圖片
            is_vid = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_img = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            
            if is_vid or is_img:
                st.error("此檔案涉及版權保護，不開放對外預覽。")
                if st.button("🏠 回到首頁"): st.query_params.clear(); st.rerun()
                return
                
            st.subheader(f"🎵 作品預覽：{item['short']}")
            # 💡 此處新增您要求的外部連結警語
            st.warning("⚠️ 此連結僅供參考，未經授權請勿分享或錄製，如有違規可能涉及法律裁處，務必知悉。")

            b64 = get_audio_base64(item['link'])
            if b64:
                st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # 5.4 登入檢查 (無 ID 參數時進入此流程)
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            pw = st.text_input("請輸入內部資料庫密碼", type="password")
            if st.form_submit_button("解鎖系統", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        return

    # 5.5 搜尋介面 (登入後可見)
    search_query = st.text_input("🔍 關鍵字搜尋 (比對標題內容)")
    if 'last_search' not in st.session_state or st.session_state.last_search != search_query:
        st.session_state.display_count = 20
        st.session_state.last_search = search_query

    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 分類過濾", ["全部"] + cat_list)
    with c2:
        # 💡 已在此處新增 "demo" 選項
        type_filter = st.radio("📑 類型過濾", ["全部", "企頻", "新鮮視", "側帶", "demo"], horizontal=True)

    # 搜尋邏輯：比對原始 Title 欄位
    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部":
        mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    total_results = len(results)
    
    # 渲染列表 (分頁載入)
    current_results = results.head(st.session_state.display_count)
    for _, row in current_results.iterrows():
        uid = row['uid']
        display_name = row['short']
        t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
        
        is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
        # 💡 將 demo 納入影片類保護邏輯
        is_video = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
        is_image = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

        with st.expander(f"📄 {display_name}"):
            if is_audio:
                if st.button("▶️ 載入音訊", key=f"p_{uid}"):
                    b64 = get_audio_base64(row['link'])
                    if b64: st.audio(b64)
            elif is_video:
                st.info("📺 影片預覽：限同仁點擊下方『開啟檔案』觀看。")
            elif is_image:
                st.warning("🖼️ 此為『圖片檔』，不是『影像檔』。同仁請點擊下方『開啟檔案』查看。")
            else:
                components.iframe(get_embed_url(row['link']), height=400)
            
            bt1, bt2 = st.columns(2)
            with bt1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
            with bt2:
                if st.button("🔗 分享檔案", key=f"s_{uid}", use_container_width=True):
                    show_share_dialog(display_name, row['link'], uid, is_video=is_video, is_image=is_image)

    # 5.6 展開更多案例按鈕
    if total_results > st.session_state.display_count:
        if st.button(f"🔽 展開更多案例 (目前 {st.session_state.display_count}/{total_results})", use_container_width=True):
            st.session_state.display_count += 20
            st.rerun()

if __name__ == "__main__":
    main()
