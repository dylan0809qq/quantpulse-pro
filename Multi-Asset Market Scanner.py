import streamlit as st        # 網頁前端框架，負責產生按鈕、圖表和介面
import yfinance as yf         # 數據接口，負責從 Yahoo Finance 抓取即時股價
import pandas as pd           # 數據處理神庫，處理表格、矩陣和時間序列
import plotly.graph_objects as go  # 繪圖庫，負責產生互動式（縮放、滑動）圖表
from plotly.subplots import make_subplots  # 繪圖工具，負責把多張圖疊在一起（如 K線 + 成交量）
import numpy as np            # 數學運算庫，處理進階數值計算

# --- 1. 軟體基本設定 ---
# 設定網頁標籤標題，並將佈局設為寬版 (Wide)，讓圖表更美觀
st.set_page_config(page_title="QuantPulse Pro - Full Suite", layout="wide")
# 網頁大標題
st.title("📊 QuantPulse Pro: 終極投資監控與分析終端")

# --- 2. 狀態管理 (Session State) ---
# 後端概念：網頁每點一個按鈕都會重新整理，Session State 讓程式能「記住」你新增的股票清單
if 'watch_list' not in st.session_state:
    # 第一次啟動時，預設追蹤這四支股票
    st.session_state.watch_list = ["VOO", "0050.TW", "NVDA", "AAPL"]

# --- 3. 側邊欄 (Sidebar)：包含清單管理與全域掃描器 ---
with st.sidebar:
    st.header("📂 投資清單管理")
    
    # A. 新增股票功能
    # 文字輸入框，.upper() 強制轉大寫，.strip() 去掉多餘空格
    new_stock = st.text_input("輸入股票代號 (如: TSLA, 2330.TW)", "").upper().strip()
    if st.button("➕ 加入追蹤"):
        if new_stock and new_stock not in st.session_state.watch_list:
            st.session_state.watch_list.append(new_stock) # 加入清單
            st.rerun() # 立即重新整理畫面以顯示新清單
    
    st.write("---")
    
    # B. 全自動均線警報燈 (後端監控邏輯)
    st.subheader("⚠️ 即時均線警報")
    if st.session_state.watch_list:
        # 顯示一個載入中的狀態欄
        with st.status("正在掃描市場數據...", expanded=True):
            for stock in st.session_state.watch_list:
                try:
                    # 抓取過去 250 天的數據 (一年約有 250 個交易日)
                    q_data = yf.download(stock, period="250d", progress=False)
                    if not q_data.empty:
                        # 處理 MultiIndex (yfinance 特有的多重欄位標籤問題)
                        cp = q_data['Close']
                        if isinstance(cp, pd.DataFrame): cp = cp.iloc[:, 0]
                        
                        # 取得最後一天的收盤價與 200 日均線值
                        last_p = float(cp.iloc[-1])
                        ma200_val = float(cp.rolling(window=200).mean().iloc[-1])
                        
                        # 邏輯判斷：跌破均線就顯示紅色錯誤，否則顯示綠色成功
                        if last_p < ma200_val:
                            st.error(f"❌ {stock}: 跌破 MA200")
                        else:
                            st.success(f"✅ {stock}: 運行正常")
                except:
                    st.warning(f"無法掃描 {stock}")

    st.write("---")
    
    # C. 定期定額參數設定 (讓使用者調整模擬數值)
    st.header("💰 定期定額設定")
    monthly_investment = st.number_input("每月投入金額", value=10000, step=1000)
    invest_years = st.slider("投資年限 (年)", 1, 30, 10)
    expected_rate = st.slider("預估年化報酬率 (%)", 1, 20, 10)

    st.write("---")
    
    # D. 管理與刪除功能
    st.subheader("清單維護")
    for stock in st.session_state.watch_list:
        c1, c2 = st.columns([3, 1])
        c1.write(stock)
        # 刪除按鈕，key 必須唯一，否則會報錯
        if c2.button("🗑️", key=f"del_{stock}"):
            st.session_state.watch_list.remove(stock)
            st.rerun()

# --- 4. 主畫面：詳細數據分析 ---
if not st.session_state.watch_list:
    st.info("💡 請在左側輸入股票代號開始您的投資旅程。")
else:
    # 讓使用者從清單中選一個要「詳細看圖」的標的
    target = st.selectbox("🎯 選擇詳細分析標的", st.session_state.watch_list)
    
    try:
        # 下載 2 年的數據，確保 MA200 指標計算有足夠的基準
        df = yf.download(target, period="2y", progress=False)
        
        if not df.empty:
            # 數據清洗：確保欄位只有一層，避免 yfinance 更新導致的錯誤
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # --- 技術指標計算 ---
            # 計算 200 日移動平均線 (MA200)
            df['MA200'] = df['Close'].rolling(window=200).mean()
            
            # 計算 RSI (相對強弱指標)
            delta = df['Close'].diff() # 計算每日價差
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean() # 14天漲幅平均
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() # 14天跌幅平均
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # --- A. 智慧警報顯示 (主畫面提示) ---
            curr_p = float(df['Close'].iloc[-1])
            curr_ma = float(df['MA200'].iloc[-1])
            
            # 使用醒目的 Banner 告訴使用者目前狀態
            if curr_p < curr_ma:
                st.error(f"🚨 【注意】{target} 目前股價 ${curr_p:.2f} 低於 200MA (${curr_ma:.2f})。")
            else:
                st.success(f"📈 【正常】{target} 目前股價 ${curr_p:.2f} 高於 200MA (${curr_ma:.2f})。")

            # --- B. TradingView 級互動圖表 (K線 + 成交量) ---
            # 建立上下兩個子圖，共用 X 軸，高度比例為 7:3
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.03, row_heights=[0.7, 0.3])

            # 繪製 K 線圖 (Candlestick)
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name="K線"
            ), row=1, col=1)

            # 疊加 MA200 均線 (橘色虛線)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="200MA", 
                                     line=dict(color='orange', width=2)), row=1, col=1)

            # 繪製成交量柱狀圖，並根據漲跌變色
            vol_colors = ['#ef5350' if df['Open'].iloc[i] > df['Close'].iloc[i] else '#26a69a' for i in range(len(df))]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=vol_colors), row=2, col=1)

            # 圖表美化：深色模式、隱藏滑動條、開啟十字準星
            fig.update_layout(height=500, template="plotly_dark", hovermode='x unified', xaxis_rangeslider_visible=False)
            
            # 加入時間縮放按鈕 (6個月、1年、全部)
            fig.update_xaxes(rangeselector=dict(buttons=list([
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="ALL")
            ])), row=1, col=1)
            
            # 在 Streamlit 顯示圖表
            st.plotly_chart(fig, use_container_width=True)

            # --- C. 定期定額複利模擬計算 ---
            st.divider() # 畫一條分隔線
            st.subheader("💰 定期定額成長曲線")
            
            # 複利數學公式：每月投入，按月計息
            months = invest_years * 12
            monthly_rate = (1 + expected_rate/100)**(1/12) - 1 # 將年利率轉為月利率
            dates = pd.date_range(start=pd.Timestamp.now(), periods=months, freq='ME') # 生成未來時間軸
            
            p_list = [monthly_investment * (i+1) for i in range(months)] # 計算本金增長
            t_list = [] # 本利和增長
            curr_sum = 0
            for i in range(months):
                curr_sum = (curr_sum + monthly_investment) * (1 + monthly_rate) # 複利公式：(現有+投入)*利率
                t_list.append(curr_sum)

            # 顯示資訊卡片：使用 metric 元件顯示數值
            k1, k2, k3 = st.columns(3)
            k1.metric("累積投入本金", f"${p_list[-1]:,.0f}")
            k2.metric("預估總資產", f"${t_list[-1]:,.0f}")
            k3.metric("淨利預測", f"${t_list[-1] - p_list[-1]:,.0f}", delta=f"{((t_list[-1]/p_list[-1])-1)*100:.1f}%")

            # 繪製複利填充圖
            fig_dca = go.Figure()
            fig_dca.add_trace(go.Scatter(x=dates, y=t_list, fill='tozeroy', name="總價值", line=dict(color='#00CC96')))
            fig_dca.add_trace(go.Scatter(x=dates, y=p_list, name="投入本金", line=dict(color='#AB63FA', dash='dot')))
            fig_dca.update_layout(height=400, template="plotly_dark", hovermode="x unified")
            st.plotly_chart(fig_dca, use_container_width=True)

    except Exception as e:
        # 如果中間有任何一步出錯，顯示紅色的錯誤訊息
        st.error(f"數據讀取失敗：{e}")

# --- 5. 底部資訊 ---
st.divider()
st.caption("QuantPulse Pro v1.0 | 投資有風險，入市需謹慎。")
# 為什麼要用 st.session_state？

# 回答： 「因為 Streamlit 的執行機制是『每次互動都會重新執行整個腳本』。如果不用 session_state，我新增的股票清單會在下一次點擊按鈕時消失。這展現了我對 Web 持久化狀態 (State Persistence) 的理解。」

# 你是如何處理數據不穩定的問題 (Data Robustness)？

# 回答： 「在抓取 yfinance 數據後，我發現它有時會回傳 MultiIndex 結構，這會導致繪圖報錯。因此我實作了 Data Cleaning (數據清洗) 邏輯，強迫數據結構統一為單層索引。同時，我也使用了 try...except 來確保單一股票數據損毀時，不會導致整個後端系統崩潰。」

# 這個複利模型是怎麼算的？

# 回答： 「我採用了離散時間複利模型 (Discrete Time Compound Model)。每一期的期初投入會與上一期的本利和相加，再乘以該月的月複合利率。這比簡單的單利計算更符合實際投資情況。」

# 關於性能優化？

# 回答： 「在側邊欄掃描器中，我加入了 st.status 容器與 spinner 效果。這在後端開發中屬於 Asynchronous UI Feedback (非同步 UI 回饋) 的概念，能顯著改善使用者在等待大量 API 請求（如同時下載多支股票）時的焦慮感。」