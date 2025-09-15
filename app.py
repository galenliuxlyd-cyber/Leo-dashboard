import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import akshare as ak
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# 设置页面
st.set_page_config(page_title="离火大运监控看板", layout="wide")
st.title("🔥 离火大运趋势投资系统监控看板")

# 简化持仓配置 - 只保留核心标的
PORTFOLIO = [
    {"category": "美股核心", "symbol": "XLK", "name": "科技ETF", "source": "yfinance"},
    {"category": "美股核心", "symbol": "XLV", "name": "医疗ETF", "source": "yfinance"},
    {"category": "A股赛道", "symbol": "588200", "name": "科创芯片", "source": "akshare"},
    {"category": "A股医药三角", "symbol": "588860", "name": "科创医药", "source": "akshare"},
    {"category": "港股医药三角", "symbol": "159892", "name": "恒生医药", "source": "akshare"},
    {"category": "港股核心", "symbol": "513180", "name": "恒生科技", "source": "akshare"},
    {"category": "美股核心", "symbol": "513300", "name": "纳指ETF", "source": "akshare"},
    {"category": "黄金", "symbol": "518880", "name": "黄金ETF", "source": "akshare"},
    {"category": "违规模个股", "symbol": "NVDA", "name": "英伟达", "source": "yfinance"},
    {"category": "违规模个股", "symbol": "TSLA", "name": "特斯拉", "source": "yfinance"},
    {"category": "违规模个股", "symbol": "0700.HK", "name": "腾讯控股", "source": "yfinance"},
]

# 计算ATR函数 (修复版)
def calculate_atr(df, period=14):
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    except Exception as e:
        st.error(f"计算ATR时出错: {e}")
        return pd.Series(np.nan, index=df.index)

# 计算技术指标函数 (简化版)
def calculate_technicals(df):
    if df.empty or len(df) < 65:  # 确保有足够的数据计算61日EMA
        return df
    
    try:
        # 计算EMA61
        df['ema61'] = df['Close'].ewm(span=61, adjust=False).mean()
        
        # 计算ATR
        df['atr14'] = calculate_atr(df)
        
        # 计算N日高点
        n_period = 20
        df['n_high'] = df['High'].rolling(window=n_period).max()
        
        # 计算动态止盈价
        df['dynamic_exit'] = df['n_high'] - 3 * df['atr14']
        
        # 计算距离止盈跌幅
        df['exit_distance_pct'] = (df['Close'] - df['dynamic_exit']) / df['Close']
        
        # 判断趋势状态
        df['trend_status'] = np.where(df['Close'] > df['ema61'], '🟢 多头', '🔴 空头')
        
    except Exception as e:
        st.error(f"计算技术指标时出错: {e}")
    
    return df

# 获取数据函数 - 使用yfinance
def get_data_yfinance(symbol, name):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        # 下载数据
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            st.warning(f"未获取到 {name}({symbol}) 的数据")
            return pd.DataFrame()
            
        return data
        
    except Exception as e:
        st.error(f"获取 {name}({symbol}) 数据失败: {e}")
        return pd.DataFrame()

# 获取数据函数 - 使用akshare
def get_data_akshare(symbol, name):
    try:
        # 获取股票历史数据
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                               start_date="20240101", 
                               end_date=datetime.now().strftime('%Y%m%d'))
        
        if df.empty:
            st.warning(f"未获取到 {name}({symbol}) 的数据")
            return pd.DataFrame()
        
        # 重命名列以匹配yfinance格式
        df.rename(columns={
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume'
        }, inplace=True)
        
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
        
    except Exception as e:
        st.error(f"获取 {name}({symbol}) 数据失败: {e}")
        return pd.DataFrame()

# 生成操作建议
def generate_action(row):
    if pd.isna(row.get('Close')) or pd.isna(row.get('ema61', np.nan)):
        return '⏳ 数据不足'
    
    if '违规' in row['category']:
        return '🚨 违反宪法'
    
    if row.get('trend_status', '') == '🔴 空头':
        return '🔴 破位清仓'
    
    exit_pct = row.get('exit_distance_pct', 0)
    if not pd.isna(exit_pct) and exit_pct < 0:
        return '🎯 触发止盈'
    
    return '🟢 持有'

# 主程序
def main():
    all_data = []
    
    for item in PORTFOLIO:
        try:
            with st.spinner(f"正在获取 {item['name']} 数据..."):
                if item['source'] == 'yfinance':
                    df = get_data_yfinance(item['symbol'], item['name'])
                else:  # akshare
                    df = get_data_akshare(item['symbol'], item['name'])
                
                if not df.empty and len(df) > 65:
                    df = calculate_technicals(df)
                    if not df.empty:
                        latest = df.iloc[-1].copy()
                        latest['symbol'] = item['symbol']
                        latest['name'] = item['name']
                        latest['category'] = item['category']
                        all_data.append(latest)
        except Exception as e:
            st.error(f"处理 {item['name']} 时出错: {e}")
        
        # 添加短暂延迟，避免请求过于频繁
        time.sleep(0.5)
    
    if all_data:
        df_dashboard = pd.DataFrame(all_data)
        df_dashboard['action'] = df_dashboard.apply(generate_action, axis=1)
        
        # 显示监控仪表板
        st.subheader("持仓监控仪表板")
        
        # 选择要显示的列
        display_columns = ['symbol', 'name', 'category', 'Close', 'ema61', 
                          'trend_status', 'dynamic_exit', 'exit_distance_pct', 'action']
        
        # 确保所有列都存在
        available_columns = [col for col in display_columns if col in df_dashboard.columns]
        
        # 格式化显示
        display_df = df_dashboard[available_columns].copy()
        if 'Close' in display_df.columns:
            display_df['Close'] = display_df['Close'].round(2)
        if 'ema61' in display_df.columns:
            display_df['ema61'] = display_df['ema61'].round(2)
        if 'dynamic_exit' in display_df.columns:
            display_df['dynamic_exit'] = display_df['dynamic_exit'].round(2)
        if 'exit_distance_pct' in display_df.columns:
            display_df['exit_distance_pct'] = (display_df['exit_distance_pct'] * 100).round(2)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # 选择标的显示详细图表
        st.subheader("个股技术分析")
        options = [f"{item['symbol']} - {item['name']}" for item in PORTFOLIO]
        selected_symbol = st.selectbox("选择标的", options)
        symbol = selected_symbol.split(' - ')[0]
        selected_item = next((item for item in PORTFOLIO if item['symbol'] == symbol), None)
        
        if selected_item:
            if selected_item['source'] == 'yfinance':
                df_selected = get_data_yfinance(selected_item['symbol'], selected_item['name'])
            else:
                df_selected = get_data_akshare(selected_item['symbol'], selected_item['name'])
                
            if not df_selected.empty:
                df_selected = calculate_technicals(df_selected)
                
                # 创建图表
                fig = go.Figure()
                
                # 添加K线
                fig.add_trace(go.Candlestick(
                    x=df_selected.index,
                    open=df_selected['Open'],
                    high=df_selected['High'],
                    low=df_selected['Low'],
                    close=df_selected['Close'],
                    name='K线'
                ))
                
                # 添加EMA61线
                if 'ema61' in df_selected.columns:
                    fig.add_trace(go.Scatter(
                        x=df_selected.index,
                        y=df_selected['ema61'],
                        name='61日EMA',
                        line=dict(color='orange', width=2)
                    ))
                
                # 添加移动止盈线
                if 'dynamic_exit' in df_selected.columns:
                    fig.add_trace(go.Scatter(
                        x=df_selected.index,
                        y=df_selected['dynamic_exit'],
                        name='移动止盈线',
                        line=dict(color='red', width=2, dash='dash')
                    ))
                
                fig.update_layout(
                    title=f"{selected_item['name']} 技术分析",
                    xaxis_title='日期',
                    yaxis_title='价格',
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示最新数据
                if not df_selected.empty:
                    latest = df_selected.iloc[-1]
                    cols = st.columns(4)
                    
                    if 'Close' in latest:
                        cols[0].metric("最新价", f"{latest['Close']:.2f}")
                    
                    if 'ema61' in latest and not pd.isna(latest['ema61']):
                        change_pct = ((latest['Close'] - latest['ema61']) / latest['ema61'] * 100) if 'Close' in latest else 0
                        cols[1].metric("61日EMA", f"{latest['ema61']:.2f}", 
                                      f"{change_pct:.2f}%")
                    
                    if 'exit_distance_pct' in latest and not pd.isna(latest['exit_distance_pct']):
                        cols[2].metric("距止盈跌幅", f"{latest['exit_distance_pct'] * 100:.2f}%")
                    
                    if 'trend_status' in latest:
                        cols[3].metric("趋势状态", latest['trend_status'])
    else:
        st.warning("未能获取足够数据，请检查网络连接和代码配置")
        st.info("提示: 某些标的可能需要更长时间获取数据，请刷新页面重试")

if __name__ == "__main__":
    main()
