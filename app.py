import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import hashlib

# === 1. 設定區 ===
# ⚠️ 請確保這是您整份試試表「發布到網路」的 CSV 網址
# 如果多頁發布，通常需要分別取得總資料庫與 Clients 的 gid 網址。
# 這裡預設將 CSV_URL 作為總資料庫，CSV_LOGO_URL 作為 Clients 分頁
# (請將下面改成您 Clients 分頁發布為 CSV 的實際網址，或是維持同一個試算表讀取)
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?output=csv"
CSV_LOGO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=2040608076&single=true&output=csv" # 範例：請換成您 Clients 分頁的 CSV 連結

PASSWORD = "888"
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

def get_image_download_url(link):
    """💡 自動將您的 Google Drive 預覽網址轉為直連下載網址，防止破圖"""
    if "drive.google.com" in link and "/file/d/" in link:
        file_id = link.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return link

# === 3. 資料載入與過濾核心 ===
@st.cache_data(ttl=180)
def load_data():
    try:
        df = pd.read_csv(CSV_URL, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        for col in ['title', 'link', 'category', 'type', 'short']:
            if col not in df.columns: df[col] = ""
        
        df = df.fillna("")
        df['short'] = df.apply(lambda r: r['short'] if str(r['short']).strip() != "" else r['title'], axis=1)
        df = df[~df['category'].astype(str).str.contains("案例資料庫", na=False)]
        df = df[~df['link'].astype(str).str.contains('/folders/')]
        df['uid'] = df['link'].apply(generate_id)
        return df.reset_index(drop=True)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=180)
def load_logo_data():
    """💡 專門讀取您的第二個 Clients 分頁"""
    try:
        # 如果您只有單一網址且包含多頁，請改用讀取特定分頁格式，這裡預設讀取獨立發布的 Logo CSV
        logo_df = pd.read_csv(CSV_LOGO_URL, on_bad_lines='skip', engine='python')
        # 標準化欄位名稱以對齊您的截圖
        logo_df.columns = [str(c).strip().lower() for c in logo_df.columns]
        # 修正您的特定欄位命名，使其在程式中好呼叫
        logo_df = logo_df.rename(columns={
            'clients客戶名稱/品名': 'client_name',
            'logo_link': 'logo_link'
        })
        return logo_df.fillna("")
    except:
        # 防呆備用：萬一雲端讀不到，自動產生與您截圖一模一樣的基礎結構，避免系統當機
        return pd.DataFrame(columns=['category', 'client_name', 'logo_link'])

# === 4. UI 元件：分享與複製介面 ===
def render_copy_ui(label, text_to_copy, is_disabled=False, warning_msg=""):
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
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20

    df = load_data()
    logo_df = load_logo_data() # 💡 載入您的 Logo 分頁
    
    if df.empty:
        st.error("目前無法連線至資料庫，請稍後再試。")
        return

    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            t_low = str(item['title']).lower()
            tp_low = str(item['type']).lower()
            
            is_vid = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_img = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            
            if is_vid or is_img:
                st.error("此檔案涉及版權保護，不開放對外預覽。")
                if st.button("🏠 回到首頁"): st.query_params.clear(); st.rerun()
                return
                
            st.subheader(f"🎵 作品預覽：{item['short']}")
            st.warning("⚠️ 此連結僅供參考，未經授權請勿分享或錄製，如有違規可能涉及法律裁處，務必知悉。")

            b64 = get_audio_base64(item['link'])
            if b64:
                st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return

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

    search_query = st.text_input("🔍 關鍵字搜尋 (比對標題內容)")
    if 'last_search' not in st.session_state or st.session_state.last_search != search_query:
        st.session_state.display_count = 20
        st.session_state.last_search = search_query

    c1, c2 = st.columns(2)
    with c1:
        cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
        sel_cat = st.selectbox("📂 分類過濾", ["全部"] + cat_list)
    with c2:
        type_filter = st.radio("📑 類型過濾", ["全部", "企頻", "新鮮視", "側帶", "demo"], horizontal=True)

    mask = pd.Series([True] * len(df), index=df.index)
    if search_query:
        mask &= (df['title'].str.contains(search_query, case=False) | df['category'].str.contains(search_query, case=False))
    if sel_cat != "全部":
        mask &= (df['category'] == sel_cat)
    if type_filter != "全部":
        mask &= (df['type'].str.contains(type_filter, case=False) | df['title'].str.contains(type_filter, case=False))

    results = df[mask]
    total_results = len(results)
    
    # =====================================================================
    # 🆕 雙軌聯動下載打包區 (精準對齊您的 Clients 表單欄位)
    # =====================================================================
    st.markdown("---")
    st.markdown("### 📦 案例與 Logo 雙軌下載打包區")
    
    if 'global_selected_cases' not in st.session_state:
        st.session_state.global_selected_cases = []
    if 'global_selected_logo_client' not in st.session_state:
        st.session_state.global_selected_logo_client = "請選擇確切客戶 Logo"

    all_available_options = list(set(st.session_state.global_selected_cases + results['short'].tolist()))

    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.markdown("**1. 挑選案例 (可跨關鍵字，最多 6 個)**")
        chosen_cases = st.multiselect(
            "請勾選要下載的案例素材：",
            options=all_available_options,
            default=st.session_state.global_selected_cases,
            max_selections=6,
        )
        st.session_state.global_selected_cases = chosen_cases
        
    with col_dl2:
        st.markdown("**2. 指派品牌 Logo (智慧大分類二階聯動)**")
        
        # 💡 智慧引導：如果選了案例，自動抓第一個案例的分類當作預設
        auto_cat_default = "全部"
        if st.session_state.global_selected_cases:
            first_case = st.session_state.global_selected_cases[0]
            matched_row = df[df['short'] == first_case]
            if not matched_row.empty:
                auto_cat_default = matched_row.iloc[0]['category']

        # A 選單：先挑大分類（對應您的 04.鮮零食飲品 等）
        logo_cat_options = ["全部"] + sorted(list(logo_df['category'].unique()))
        default_cat_idx = logo_cat_options.index(auto_cat_default) if auto_cat_default in logo_cat_options else 0
        
        selected_logo_cat = st.selectbox(
            "第一步：縮小大分類範圍",
            options=logo_cat_options,
            index=default_cat_idx
        )
        
        # 根據 A 選單的篩選結果，動態決定 B 選單（客戶品名）裡要秀出哪些對應品牌
        if selected_logo_cat != "全部":
            filtered_logo_df = logo_df[logo_df['category'] == selected_logo_cat]
        else:
            filtered_logo_df = logo_df
            
        logo_client_options = ["請選擇確切客戶 Logo"] + sorted(list(filtered_logo_df['client_name'].unique()))
        
        # 確保之前的選擇如果依然在清單內，就維持選取
        default_client_idx = logo_client_options.index(st.session_state.global_selected_logo_client) if st.session_state.global_selected_logo_client in logo_client_options else 0
        
        selected_logo_client = st.selectbox(
            "第二步：選擇確切的客戶名稱/品名",
            options=logo_client_options,
            index=default_client_idx
        )
        st.session_state.global_selected_logo_client = selected_logo_client
        
    # 3. 啟動按鈕邏輯
    if st.session_state.global_selected_cases and st.session_state.global_selected_logo_client != "請選擇確切客戶 Logo":
        st.success(f"✅ 準備就緒！已記住 {len(st.session_state.global_selected_cases)} 個案例，將搭配「{st.session_state.global_selected_logo_client}」的 Logo。")
        
        c_btn1, c_btn2 = st.columns([4, 1])
        with c_btn1:
            if st.button("🚀 開始打包下載選定素材", use_container_width=True):
                # 從 logo_df 撈出對應的真實 Google Drive 網址
                final_logo_row = logo_df[logo_df['client_name'] == st.session_state.global_selected_logo_client]
                raw_logo_url = final_logo_row.iloc[0]['logo_link'] if not final_logo_row.empty else ""
                real_download_logo_url = get_image_download_url(raw_logo_url)
                
                st.info(f"系統準備下載 Logo 直連網址: {real_download_logo_url}")
                st.info("正在同時抓取這 6 個案例與對應圖片中...（打包整合中）")
                
        with c_btn2:
            if st.button("🗑️ 清空重選", use_container_width=True):
                st.session_state.global_selected_cases = []
                st.session_state.global_selected_logo_client = "請選擇確切客戶 Logo"
                st.rerun()
            
    else:
        st.warning("💡 請先「勾選案例」並挑選「確切客戶 Logo」，即可開啟下載打包功能。")
        
    st.markdown("---")

    # 5.6 渲染列表 (分頁載入)
    current_results = results.head(st.session_state.display_count)
    for _, row in current_results.iterrows():
        uid = row['uid']
        display_name = row['short']
        t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
        
        is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
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

    if total_results > st.session_state.display_count:
        if st.button(f"🔽 展開更多案例 (目前 {st.session_state.display_count}/{total_results})", use_container_width=True):
            st.session_state.display_count += 20
            st.rerun()

if __name__ == "__main__":
    main()
