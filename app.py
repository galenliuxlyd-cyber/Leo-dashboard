import streamlit as st
import pandas as pd
import numpy as np
import tushare as ts
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 设置页面
st.set_page_config(page_title="离火大运监控看板", layout="wide")
st.title("🔥 离火大运趋势投资系统监控看板")

# 初始化Tushare
YOUR_TUSHARE_TOKEN = '24f91dbe17ae2ec62eda84014475c5249a61900f266b59270687a09c'  # TODO: 替换为你的实际Token！
pro = ts.pro_api(YOUR_TUSHARE_TOKEN)

# 持仓配置
PORTFOLIO = [
    {"category": "观察", "symbol": "YXIC", "name": "纳斯达克指数", "ts_code": "YXIC.US", "exchange": "US"},
    {"category": "观察", "symbol": "HSTECH", "name": "恒生科技指数", "ts_code": "HSTECH.HK", "exchange": "HK"},
    {"category": "观察", "symbol": "000001", "name": "上证指数", "ts_code": "000001.SH", "exchange": "SH"},
    {"category": "美股核心", "symbol": "XLK", "name": "科技ETF", "ts_code": "XLK.US", "exchange": "US"},
    {"category": "美股核心", "symbol": "XLV", "name": "医疗ETF", "ts_code": "XLV.US", "exchange": "US"},
    {"category": "A股赛道", "symbol": "516630", "name": "云计算50", "ts_code": "516630.SH", "exchange": "SH"},
    {"category": "A股赛道", "symbol": "588200", "name": "科创芯片", "ts_code": "588200.SH", "exchange": "SH"},
    {"category": "A股医药三角", "symbol": "588860", "name": "科创医药", "ts_code": "588860.SH", "exchange": "SH"},
    {"category": "港股医药三角", "symbol": "159892", "name": "恒生医药", "ts_code": "159892.SZ", "exchange": "SZ"},
    {"category": "港股医药三角", "symbol": "159316", "name": "恒生创新药", "ts_code": "159316.SZ", "exchange": "SZ"},
    {"category": "港股核心", "symbol": "513180", "name": "恒生科技", "ts_code": "513180.SH", "exchange": "SH"},
    {"category": "美股核心", "symbol": "513300", "name": "纳指", "ts_code": "513300.SH", "exchange": "SH"},
    {"category": "黄金", "symbol": "518880", "name": "黄金", "ts_code": "518880.SH", "exchange": "SH"},
    {"category": "违规模个股", "symbol": "NVDA", "name": "英伟达", "ts_code": "NVDA.US", "exchange": "US"},
    {"category": "违规模个股", "symbol": "TSLA", "name": "特斯拉", "ts_code": "TSLA.US", "exchange": "US"},
    {"category": "违规模个股", "symbol": "00700", "name": "腾讯控股", "ts_code": "00700.HK", "exchange": "HK"},
    {"category": "违规ST股", "symbol": "002425", "name": "ST凯文", "ts_code": "002425.SZ", "exchange": "SZ"},
    {"category": "违规模个股", "symbol": "000559", "name": "万向钱潮", "ts_code": "000559.SZ", "exchange": "SZ"},
    {"category": "违规模个股", "symbol": "600654", "name": "中安科", "ts_code": "600654.SH", "exchange": "SH"},
    {"category": "违规模个股", "symbol": "002004", "name": "华邦健康", "ts_code": "002004.SZ", "exchange": "SZ"},
]

# 计算技术指标函数
def calculate_technicals(df):
    df['ema61'] = df['close'].ewm(span=61, adjust=False).mean()
    df['atr14'] = calculate_atr(df, 14)
    df['n_high_20'] = df['high'].rolling(window=20).max() # 计算20日最高价
    df['dynamic_exit'] = df['n_high_20'] - 3 * df['atr14'] # 动态止盈价
    df['exit_distance_pct'] = (df['close'] - df['dynamic_exit']) / df['close'] # 距离止盈跌幅
    df['trend_status'] = np.where(df['close'] > df['ema61'], '🟢 多头', '🔴 空头')
    return df

# 计算ATR函数
def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(period).mean()
    return atr

# 获取数据函数
@st.cache_data(ttl=6*3600) # 缓存6小时
def get_data(ts_code, exchange):
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=100)).strftime('%Y%m%d') 
    try:
        if exchange in ['SH', 'SZ']:
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            df = df.sort_values('trade_date')
            df.rename(columns={'trade_date': 'date', 'ts_code': 'symbol', 'close': 'close', 'high': 'high', 'low': 'low', 'vol': 'volume'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            return calculate_technicals(df)
        elif exchange == 'US':
            symbol = ts_code.replace('.US', '')
            df = yf.download(symbol, start=start_date, end=end_date)
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date', 'Close': 'close', 'High': 'high', 'Low': 'low', 'Volume': 'volume'}, inplace=True)
            df.set_index('date', inplace=True)
            return calculate_technicals(df)
        elif exchange == 'HK':
            symbol = ts_code.replace('.HK', '')
            df = yf.download(symbol + '.HK', start=start_date, end=end_date)
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date', 'Close': 'close', 'High': 'high', 'Low': 'low', 'Volume': 'volume'}, inplace=True)
            df.set_index('date', inplace=True)
            return calculate_technicals(df)
    except Exception as e:
        st.error(f"获取 {ts_code} 数据失败: {e}")
    return pd.DataFrame()

# 生成操作建议
def generate_action(row):
    if row['category'] in ['违规模个股', '违规ST股']:
        return '🚨 违反宪法，清仓/减持'
    if row['trend_status'] == '🔴 空头':
        return '🔴 生命线破位，清仓'
    if row['exit_distance_pct'] < 0:
        return '🎯 触发移动止盈，清仓'
    if pd.isna(row['ema61']):
        return '⏳ 数据不足，观察'
    return '🟢 持有'

# 主程序
def main():
    all_data = []
    for item in PORTFOLIO:
        with st.spinner(f"正在获取 {item['name']} 数据..."):
            df = get_data(item['ts_code'], item['exchange'])
            if not df.empty:
                latest = df.iloc[-1].to_dict()
                latest['symbol'] = item['symbol']
                latest['name'] = item['name']
                latest['category'] = item['category']
                all_data.append(latest)
    
    if all_data:
        df_dashboard = pd.DataFrame(all_data)
        df_dashboard['action'] = df_dashboard.apply(generate_action, axis=1)
        
        # 显示监控仪表板
        st.subheader("持仓监控仪表板")
        st.dataframe(
            df_dashboard[[
                'symbol', 'name', 'category', 'close', 'ema61', 
                'trend_status', 'dynamic_exit', 'exit_distance_pct', 'action'
            ]].round(2),
            use_container_width=True
        )
        
        # 选择标的显示详细图表
        st.subheader("个股技术分析")
        selected_symbol = st.selectbox("选择标的", [f"{item['symbol']} - {item['name']}" for item in PORTFOLIO])
        symbol = selected_symbol.split(' - ')[0]
        selected_item = next((item for item in PORTFOLIO if item['symbol'] == symbol), None)
        
        if selected_item:
            df_selected = get_data(selected_item['ts_code'], selected_item['exchange'])
            if not df_selected.empty:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df_selected.index,
                    open=df_selected['open'], high=df_selected['high'],
                    low=df_selected['low'], close=df_selected['close'],
                    name='K线'))
                fig.add_trace(go.Scatter(x=df_selected.index, y=df_selected['ema61'], 
                    name='61日EMA', line=dict(color='orange', width=2)))
                fig.add_trace(go.Scatter(x=df_selected.index, y=df_selected['dynamic_exit'], 
                    name='移动止盈线', line=dict(color='red', width=2, dash='dash')))
                fig.update_layout(title=f"{selected_item['name']} 技术分析", 
                                xaxis_title='日期', yaxis_title='价格')
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示最新数据
                col1, col2, col3 = st.columns(3)
                latest = df_selected.iloc[-1]
                col1.metric("最新价", f"{latest['close']:.2f}")
                col2.metric("61日EMA", f"{latest['ema61']:.2f}", 
                          f"{'above' if latest['close'] > latest['ema61'] else 'below'}")
                col3.metric("距止盈跌幅", f"{latest['exit_distance_pct']*100:.2f}%")
    else:
        st.error("未能获取任何数据，请检查网络连接和API配置")

if __name__ == "__main__":
    main()
