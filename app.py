import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import io
import base64
import hashlib
import os
import tempfile
from datetime import datetime

# === 1. 設定區 ===
# ⚠️ 請確保這兩個網址分別是「總資料庫」分頁與「Clients」分頁獨立發布為 CSV 的網址
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=0&single=true&output=csv"
CSV_LOGO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnViFsUwWYASaR5i1PefsWE4b6-5wwqTbJFJG8vysgcHYZDKzq-wwK4hM4xOtet3B65UjohzRjh38C/pub?gid=1588470763&single=true&output=csv" # 👈 請務必填入 Clients 分頁專屬的 CSV 網址

PASSWORD = "888"
SITE_URL = "https://swd-case.streamlit.app" 

# 💡 預設的去背高畫質小喇叭圖標網址，用來當作 PPT 內音軌的精美顯示外觀
DEFAULT_SPEAKER_ICON_URL = "https://img.icons8.com/color/96/speaker.png"

# === 2. 核心技術函數 ===
def generate_id(link):
    return hashlib.md5(str(link).encode()).hexdigest()[:10]

@st.cache_data(ttl=120)
def get_audio_base64(url):
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
    if "drive.google.com" in link and "/view" in link:
        return link.replace("/view", "/preview")
    return link

# === 3. 資料載入與過濾核心 ===
@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
def load_logo_data():
    try:
        logo_df = pd.read_csv(CSV_LOGO_URL, on_bad_lines='skip', engine='python')
        logo_df.columns = [str(c).strip().lower() for c in logo_df.columns]
        
        rename_dict = {}
        for c in logo_df.columns:
            if 'client' in c or '客戶' in c or '品名' in c or 'brand' in c:
                rename_dict[c] = 'client_name'
            if 'link' in c or '網址' in c or 'logo' in c:
                rename_dict[c] = 'logo_link'
            if 'category' in c or '分類' in c:
                rename_dict[c] = 'category'
                
        logo_df = logo_df.rename(columns=rename_dict)
        if 'client_name' not in logo_df.columns and len(logo_df.columns) > 1:
            logo_df.columns.values[1] = 'client_name'
            
        return logo_df.fillna("")
    except:
        return pd.DataFrame(columns=['category', 'client_name', 'logo_link'])

# === 5. 主程式架構 ===
def main():
    st.set_page_config(page_title="全家通路媒體資料庫", layout="centered")
    
    # 注入樣式，強制隱藏右下角的 "Press Enter to apply" 英文
    st.markdown("""
        <style>
        .stTextInput div[data-testid="stWidgetInstructions"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 20
    if 'selected_uids' not in st.session_state:
        st.session_state.selected_uids = []
    if 'confirmed_stage' not in st.session_state:
        st.session_state.confirmed_stage = False

    df = load_data()
    logo_df = load_logo_data()
    
    if df.empty:
        st.error("目前無法連線至總資料庫，請檢查發布設定。")
        return

    params = st.query_params
    target_uid = params.get("id", None)

    if target_uid:
        target_row = df[df['uid'] == target_uid]
        if not target_row.empty:
            item = target_row.iloc[0]
            t_low, tp_low = str(item['title']).lower(), str(item['type']).lower()
            is_vid = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_img = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            if is_vid or is_img:
                st.error("此檔案涉及版權保護，不開放對外預覽。")
                return
            st.subheader(f"🎵 作品預覽：{item['short']}")
            b64 = get_audio_base64(item['link'])
            if b64: st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            if st.button("🏠 回到首頁"): st.query_params.clear(); st.rerun()
            return

    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>🔒 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            pw = st.text_input("請輸入內部資料庫密碼", type="password")
            if st.form_submit_button("解鎖系統", use_container_width=True):
                if pw == PASSWORD: st.session_state.logged_in = True; st.rerun()
                else: st.error("密碼錯誤")
        return

    # -----------------------------------------------------------------
    # 【第一階段】常駐戰情管理台 + 搜尋列表
    # -----------------------------------------------------------------
    if not st.session_state.confirmed_stage:
        st.markdown("<h2 style='text-align: center;'>📂 全家通路媒體資料庫</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.selected_uids:
            st.markdown("### 📊 戰情管理台 (已挑選項目)")
            for idx, uid in enumerate(st.session_state.selected_uids):
                matched_rows = df[df['uid'] == uid]
                if matched_rows.empty: continue
                case_info = matched_rows.iloc[0]
                
                col_name, col_audio, col_del = st.columns([5, 4, 1])
                with col_name:
                    st.caption(f"**項目 {idx+1}**")
                    st.markdown(f"📄 {case_info['short']}")
                with col_audio:
                    t_low = str(case_info['title']).lower()
                    is_audio_file = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in str(case_info['type']).lower()
                    
                    if is_audio_file:
                        if st.button("▶️ 載入音訊", key=f"panel_play_{uid}", use_container_width=True):
                            with st.spinner("載入中..."):
                                b64 = get_audio_base64(case_info['link'])
                                if b64: st.audio(b64)
                    else:
                        st.caption("📺 影片/圖像檔 (不開放網頁試聽)")
                with col_del:
                    st.markdown("剔除")
                    if st.button("❌", key=f"panel_del_{uid}", use_container_width=True):
                        st.session_state.selected_uids.remove(uid)
                        st.rerun()
            st.markdown("---")

        c_status, c_ok = st.columns([3, 2])
        with c_status:
            st.markdown(f"📥 已挑選進度： **{len(st.session_state.selected_uids)} / 6**")
        with c_ok:
            if st.button("👌 確認挑選項目", use_container_width=True, key="confirm_selection_main_btn", type="primary" if st.session_state.selected_uids else "secondary"):
                if st.session_state.selected_uids:
                    st.session_state.confirmed_stage = True
                    st.rerun()
                else: st.warning("請先在下方案例旁勾選！")

        st.markdown("---")
        
        search_query = st.text_input("🔍 關鍵字搜尋 (比對標題內容)")
        if 'last_search' not in st.session_state or st.session_state.last_search != search_query:
            st.session_state.display_count = 20
            st.session_state.last_search = search_query

        c1, c2 = st.columns(2)
        with c1:
            cat_list = sorted([str(x) for x in df['category'].unique() if str(x).strip()])
            sel_cat = st.selectbox("📂 總資料庫分類過濾", ["全部"] + cat_list)
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
        
        st.markdown("#### 📂 搜尋結果案例列表 (請在下方挑選打勾)")
        current_results = results.head(st.session_state.display_count)
        
        for _, row in current_results.iterrows():
            uid = row['uid']
            display_name = row['short']
            t_low, tp_low = str(row['title']).lower(), str(row['type']).lower()
            
            is_audio = any(ext in t_low for ext in ['.mp3', '.wav', '.m4a']) or "企頻" in tp_low
            is_video = any(x in tp_low for x in ["新鮮視", "側帶", "demo"]) or any(ext in t_low for ext in ['.mp4', '.mov'])
            is_image = any(ext in t_low for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

            col_check, col_exp = st.columns([1, 9])
            with col_check:
                is_checked_before = uid in st.session_state.selected_uids
                check_clicked = st.checkbox("選取", key=f"chk_{uid}", value=is_checked_before, label_visibility="collapsed")
                if check_clicked and uid not in st.session_state.selected_uids:
                    if len(st.session_state.selected_uids) < 6:
                        st.session_state.selected_uids.append(uid)
                        st.rerun()
                    else: st.error("❌ 最多只能打包 6 個案例！")
                elif not check_clicked and uid in st.session_state.selected_uids:
                    st.session_state.selected_uids.remove(uid)
                    st.rerun()

            with col_exp:
                with st.expander(f"📄 {display_name}"):
                    if is_audio:
                        if st.button("▶️ 載入音訊", key=f"p_{uid}"):
                            b64 = get_audio_base64(row['link'])
                            if b64: st.audio(b64)
                    elif is_video: st.info("📺 影片預覽：限同仁點擊下方『開啟檔案』觀看。")
                    elif is_image: st.warning("🖼️ 此為『圖片檔』。同仁請點擊下方『開啟檔案』查看。")
                    else: components.iframe(get_embed_url(row['link']), height=400)
                    
                    bt1, bt2 = st.columns(2)
                    with bt1: st.link_button("↗ 開啟檔案", row['link'], use_container_width=True)
                    with bt2:
                        if st.button("🔗 分享檔案", key=f"s_{uid}", use_container_width=True):
                            show_share_dialog(display_name, row['link'], uid, is_video=is_video, is_image=is_image)

        if total_results > st.session_state.display_count:
            if st.button(f"🔽 展開更多案例", use_container_width=True):
                st.session_state.display_count += 20
                st.rerun()

    # -----------------------------------------------------------------
    # 【第二階段】配置與最終 PPTX 封裝生成頁面
    # -----------------------------------------------------------------
    if st.session_state.confirmed_stage and st.session_state.selected_uids:
        st.markdown("""
        <div style="background-color:#e0f2fe; padding:20px; border-radius:10px; border-left:5px solid #0284c7; margin: 15px 0;">
            <h4 style="color:#0369a1; margin:0;">🎯 第二階段：確認各案例 Logo 與自訂簡報大標</h4>
            <p style="font-size:14px; color:#0c4a6e; margin:5px 0 0 0;">請確認下方各案例對應的 Logo。音訊將嵌入小喇叭，影片將改為超連結網址。</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🖋️ 編輯 PPT 簡報大標題")
        custom_ppt_title = st.text_input("請輸入您想要的 PPT 簡報主標題：", value="合作夥伴案例分享", key="custom_ppt_title_input")
        st.markdown("---")
        
        logo_options = ["請選擇確切客戶 Logo"] + sorted(list(logo_df['client_name'].unique())) if not logo_df.empty else ["請選擇確切客戶 Logo"]
        final_pack_pairs = {}

        for idx, picked_uid in enumerate(st.session_state.selected_uids):
            matched_rows = df[df['uid'] == picked_uid]
            if matched_rows.empty: continue
            case_row = matched_rows.iloc[0]
            case_title = str(case_row['short'])
            case_type_str = str(case_row['type'])
            
            guessed_logo_for_this_row = "請選擇確切客戶 Logo"
            if not logo_df.empty:
                for client in logo_df['client_name'].unique():
                    pure_name = str(client).split('_')[-1] if '_' in str(client) else str(client)
                    if pure_name in case_title or str(client) in case_title:
                        guessed_logo_for_this_row = client
                        break
            
            c_label, c_case_lbl, c_logo_sel, c_del = st.columns([1, 4, 3, 1])
            with c_label: st.markdown(f"\n\n**案例 {idx+1}**")
            with c_case_lbl:
                st.markdown("案例名稱")
                st.info(f"📄 {case_title}")
            with c_logo_sel:
                st.markdown("對應 Logo")
                default_idx = logo_options.index(guessed_logo_for_this_row) if guessed_logo_for_this_row in logo_options else 0
                chosen_logo_for_row = st.selectbox(f"選Logo_{picked_uid}", options=logo_options, index=default_idx, key=f"sel_logo_pair_{picked_uid}", label_visibility="collapsed")
                
                logo_row = logo_df[logo_df['client_name'] == chosen_logo_for_row]
                raw_url = logo_row.iloc[0]['logo_link'] if not logo_row.empty else ""
                file_id = ""
                if "/file/d/" in raw_url: file_id = raw_url.split("/file/d/")[1].split("/")[0]
                elif "id=" in raw_url: file_id = raw_url.split("id=")[1].split("&")[0]
                
                final_pack_pairs[picked_uid] = {
                    'case_title': case_title,
                    'case_type': case_type_str,
                    'case_link': case_row['link'], 
                    'logo_name': chosen_logo_for_row,
                    'logo_file_id': file_id
                }
            with c_del:
                st.markdown("剔除")
                if st.button("❌", key=f"del_item_{picked_uid}", use_container_width=True):
                    st.session_state.selected_uids.remove(picked_uid)
                    st.rerun()

            st.markdown("<div style='margin-bottom:-10px;'></div>", unsafe_allow_html=True) 

        st.markdown("---")
        
        c_back, c_action = st.columns([1, 4])
        with c_back:
            if st.button("🔙 返回挑選更多案例", use_container_width=True, key="unique_back_btn"):
                st.session_state.confirmed_stage = False
                st.rerun()
                
        with c_action:
            if final_pack_pairs:
                from pptx import Presentation
                from pptx.util import Inches, Pt
                from pptx.enum.text import PP_ALIGN 
                
                ppt_buffer = io.BytesIO()
                
                if st.button("🎨 確認無誤！開始排版並下載六宮格提案 PPTX", use_container_width=True, key="generate_final_pptx_execution_btn", type="primary"):
                    with st.spinner("🚀 正在處理多媒體路由與 Logo 封裝中..."):
                        try:
                            prs = Presentation()
                            prs.slide_width = Inches(13.333)
                            prs.slide_height = Inches(7.5)
                            slide = prs.slides.add_slide(prs.slide_layouts[6])
                            
                            # 大標題：置中 36 級字
                            title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.133), Inches(1.0))
                            tf = title_box.text_frame
                            tf.word_wrap = True
                            p_title = tf.paragraphs[0]
                            p_title.text = str(custom_ppt_title).strip()
                            p_title.font.size = Pt(36) 
                            p_title.font.bold = True
                            p_title.font.name = "Microsoft JhengHei"
                            p_title.alignment = PP_ALIGN.CENTER 
                            
                            # 六宮格坐標
                            x_coords = [Inches(0.6), Inches(4.8), Inches(9.0)]
                            y_coords = [Inches(2.0), Inches(4.7)]
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            
                            # 下載純音軌專用去背小喇叭
                            resp_icon = requests.get(DEFAULT_SPEAKER_ICON_URL, headers=headers, timeout=5)
                            icon_bytes = resp_icon.content if resp_icon.status_code == 200 else None
                            
                            for idx, (uid, info) in enumerate(final_pack_pairs.items()):
                                if idx >= 6: break 
                                row_idx, col_idx = idx // 3, idx % 3   
                                current_x, current_y = x_coords[col_idx], y_coords[row_idx]
                                
                                # ⚡ 影音精準切分流
                                title_clean = info['case_title'].replace(" ", "").lower()
                                type_clean = info['case_type'].replace(" ", "").lower()
                                link_clean = info['case_link'].split('?')[0].lower()
                                
                                is_explicit_audio = any(ext in link_clean for ext in ['.mp3', '.m4a', '.wav'])
                                is_explicit_video = any(ext in link_clean for ext in ['.mp4', '.mov', '.avi'])
                                
                                if is_explicit_audio:
                                    is_mp4 = False
                                elif is_explicit_video:
                                    is_mp4 = True
                                else:
                                    is_mp4 = (
                                        any(k in title_clean for k in ['新鮮視', '側帶']) or 
                                        any(k in type_clean for k in ['新鮮視', '側帶'])
                                    )
                                
                                # 1. 繪製案例名稱與超連結
                                text_box = slide.shapes.add_textbox(current_x, current_y, Inches(3.8), Inches(0.6))
                                text_box.text_frame.word_wrap = True
                                p_case = text_box.text_frame.paragraphs[0]
                                
                                run = p_case.add_run()
                                run.text = f"🔹 {info['case_title']}"
                                run.font.size = Pt(11)
                                run.font.name = "Microsoft JhengHei"
                                
                                # 💡 核心改動：如果是影片案例，直接把「案例文字本身」轉綁微軟線上觀看超連結！
                                if is_mp4 and info['case_link']:
                                    run.hyperlink.address = info['case_link']
                                    run.font.underline = True # 帶底線提示可點擊
                                
                                # 2. 如果是純音訊，執行實體小喇叭嵌入
                                if not is_mp4 and info['case_link']:
                                    try:
                                        media_url = info['case_link'].split('?')[0] + "?download=1" if "sharepoint.com" in info['case_link'] else info['case_link']
                                        resp_media = requests.get(media_url, headers=headers, timeout=20)
                                        
                                        if resp_media.status_code == 200:
                                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_media:
                                                tmp_media.write(resp_media.content)
                                                tmp_media_path = tmp_media.name
                                            
                                            poster_stream = io.BytesIO(icon_bytes) if icon_bytes else None
                                            slide.shapes.add_movie(
                                                tmp_media_path,
                                                current_x + Inches(0.2),
                                                current_y + Inches(0.7),
                                                width=Inches(0.5), 
                                                height=Inches(0.5),
                                                poster_frame_image=poster_stream, 
                                                mime_type='audio/mpeg'
                                            )
                                            try: os.unlink(tmp_media_path)
                                            except: pass
                                    except: pass
                                
                                # 3. 嵌入去背品牌 Logo
                                if info.get('logo_file_id') and info['logo_name'] != "請選擇確切客戶 Logo":
                                    try:
                                        direct_img_url = f"https://lh3.googleusercontent.com/u/0/d/{info['logo_file_id']}"
                                        resp_logo = requests.get(direct_img_url, headers=headers, timeout=10)
                                        if resp_logo.status_code == 200 and len(resp_logo.content) > 1000:
                                            # 影片沒有小喇叭阻擋，Logo位置稍微拉回正中
                                            x_offset = Inches(0.6) if is_mp4 else Inches(1.0)
                                            slide.shapes.add_picture(
                                                io.BytesIO(resp_logo.content), 
                                                current_x + x_offset, 
                                                current_y + Inches(0.65), 
                                                width=Inches(1.6)
                                            )
                                    except: pass
                                        
                            prs.save(ppt_buffer)
                            ppt_buffer.seek(0)
                            today_str = datetime.now().strftime("%Y%m%d")
                            
                            st.download_button(
                                label="💾 簡報封裝完畢！點此儲存 PPTX 檔案至電腦",
                                data=ppt_buffer,
                                file_name=f"媒體通路提案簡報_{today_str}.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                use_container_width=True,
                                key="final_download_pptx_stream_btn",
                                type="primary"
                            )
                        except Exception as e:
                            st.error(f"❌ 簡報自動生成失敗，原因：{str(e)}")
            else: st.warning("⚠️ 您的挑選清單目前為空。")
        st.markdown("---")

if __name__ == "__main__":
    main()
