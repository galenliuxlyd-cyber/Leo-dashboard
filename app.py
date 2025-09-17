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

# 完整持仓配置 - 修正指数代码
PORTFOLIO = [
    {"category": "观察", "symbol": "^IXIC", "name": "纳斯达克指数", "source": "yfinance"},
    {"category": "观察", "symbol": "000001", "name": "上证指数", "source": "akshare"},
    {"category": "美股核心", "symbol": "XLK", "name": "科技ETF", "source": "yfinance"},
    {"category": "美股核心", "symbol": "XLV", "name": "医疗ETF", "source": "yfinance"},
    {"category": "A股赛道", "symbol": "516630", "name": "云计算50", "source": "akshare"},
    {"category": "A股赛道", "symbol": "588200", "name": "科创芯片", "source": "akshare"},
    {"category": "A股医药三角", "symbol": "588860", "name": "科创医药", "source": "akshare"},
    {"category": "港股医药三角", "symbol": "159892", "name": "恒生医药", "source": "akshare"},
    {"category": "港股医药三角", "symbol": "159316", "name": "恒生创新药", "source": "akshare"},
    {"category": "港股核心", "symbol": "513180", "name": "恒生科技", "source": "akshare"},
    {"category": "美股核心", "symbol": "513300", "name": "纳指ETF", "source": "akshare"},
    {"category": "黄金", "symbol": "518880", "name": "黄金ETF", "source": "akshare"},
    {"category": "违规模个股", "symbol": "NVDA", "name": "英伟达", "source": "yfinance"},
    {"category": "违规模个股", "symbol": "TSLA", "name": "特斯拉", "source": "yfinance"},
    {"category": "违规模个股", "symbol": "0700.HK", "name": "腾讯控股", "source": "yfinance"},
    {"category": "违规ST股", "symbol": "002425", "name": "ST凯文", "source": "akshare"},
    {"category": "违规模个股", "symbol": "000559", "name": "万向钱潮", "source": "akshare"},
    {"category": "违规模个股", "symbol": "600654", "name": "中安科", "source": "akshare"},
    {"category": "违规模个股", "symbol": "002004", "name": "华邦健康", "source": "akshare"},
]

# 获取数据函数 - 使用yfinance
def get_data_yfinance(symbol, name):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        # 下载数据
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            st.warning(f"未获取到 {name}({symbol}) 的数据")
            return None
            
        return data
        
    except Exception as e:
        st.error(f"获取 {name}({symbol}) 数据失败: {e}")
        return None

# 获取数据函数 - 使用akshare (带重试机制)
def get_data_akshare(symbol, name, max_retries=3):
    for attempt in range(max_retries):
        try:
            # 尝试多种方式获取数据
            df = None
            
            # 方法1: 使用基金ETF接口
            try:
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily", 
                                        start_date="20240101", 
                                        end_date=datetime.now().strftime('%Y%m%d'))
                if not df.empty:
                    df.rename(columns={
                        '日期': 'Date',
                        '开盘': 'Open',
                        '收盘': 'Close',
                        '最高': 'High',
                        '最低': 'Low',
                        '成交量': 'Volume'
                    }, inplace=True)
            except:
                pass
            
            # 方法2: 使用股票接口
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                           start_date="20240101", 
                                           end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        df.rename(columns={
                            '日期': 'Date',
                            '开盘': 'Open',
                            '收盘': 'Close',
                            '最高': 'High',
                            '最低': 'Low',
                            '成交量': 'Volume'
                        }, inplace=True)
                except:
                    pass
            
            # 方法3: 使用指数接口
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_index_hist(symbol=symbol, period="daily", 
                                               start_date="20240101", 
                                               end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        df.rename(columns={
                            '日期': 'Date',
                            '开盘': 'Open',
                            '收盘': 'Close',
                            '最高': 'High',
                            '最低': 'Low',
                            '成交量': 'Volume'
                        }, inplace=True)
                except:
                    pass
            
            if df is None or df.empty:
                if attempt == max_retries - 1:
                    st.warning(f"未获取到 {name}({symbol}) 的数据")
                continue
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            return df
            
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"获取 {name}({symbol}) 数据失败: {e}")
            time.sleep(1)  # 等待1秒后重试
    
    return None

# 计算技术指标
def calculate_technicals_simple(df):
    if df is None or df.empty or len(df) < 65:
        return None
    
    try:
        # 创建结果字典
        result = {}
        
        # 确保我们获取的是标量值而不是Series
        close_price = df['Close'].iloc[-1]
        if hasattr(close_price, 'item'):
            close_price = close_price.item()
        result['Close'] = float(close_price)
        
        # 计算EMA61
        ema61_series = df['Close'].ewm(span=61, adjust=False).mean()
        ema61 = ema61_series.iloc[-1]
        if hasattr(ema61, 'item'):
            ema61 = ema61.item()
        result['ema61'] = float(ema61)
        
        # 判断趋势状态 - 使用标量值比较
        result['trend_status'] = '🟢 多头' if result['Close'] > result['ema61'] else '🔴 空头'
        
        # 计算ATR (简化版)
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        if hasattr(atr, 'item'):
            atr = atr.item()
        result['atr14'] = float(atr)
        
        # 计算N日高点
        n_period = 20
        n_high = df['High'].rolling(window=n_period).max().iloc[-1]
        if hasattr(n_high, 'item'):
            n_high = n_high.item()
        result['n_high'] = float(n_high)
        
        # 计算动态止盈价
        result['dynamic_exit'] = result['n_high'] - 3 * result['atr14']
        
        # 计算距离止盈跌幅
        result['exit_distance_pct'] = (result['Close'] - result['dynamic_exit']) / result['Close']
        
        return result
        
    except Exception as e:
        st.error(f"计算技术指标时出错: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

# 生成操作建议
def generate_action(result, category):
    if result is None:
        return '⏳ 数据不足'
    
    if '违规' in category:
        return '🚨 违反宪法'
    
    if result.get('trend_status', '') == '🔴 空头':
        return '🔴 破位清仓'
    
    exit_pct = result.get('exit_distance_pct', 0)
    if exit_pct < 0:
        return '🎯 触发止盈'
    
    return '🟢 持有'

# 主程序
def main():
    all_data = []
    
    # 显示进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, item in enumerate(PORTFOLIO):
        status_text.text(f"正在处理 {item['name']} ({i+1}/{len(PORTFOLIO)})")
        progress_bar.progress((i+1)/len(PORTFOLIO))
        
        try:
            # 获取数据
            if item['source'] == 'yfinance':
                df = get_data_yfinance(item['symbol'], item['name'])
            else:
                df = get_data_akshare(item['symbol'], item['name'])
            
            # 计算技术指标
            if df is not None and not df.empty:
                result = calculate_technicals_simple(df)
                if result is not None:
                    result['symbol'] = item['symbol']
                    result['name'] = item['name']
                    result['category'] = item['category']
                    result['action'] = generate_action(result, item['category'])
                    all_data.append(result)
            
        except Exception as e:
            st.error(f"处理 {item['name']} 时出错: {e}")
            import traceback
            st.error(traceback.format_exc())
        
        # 添加短暂延迟
        time.sleep(0.5)
    
    # 清除进度条
    progress_bar.empty()
    status_text.empty()
    
    if all_data:
        df_dashboard = pd.DataFrame(all_data)
        
        # 显示监控仪表板
        st.subheader("持仓监控仪表板")
        
        # 选择要显示的列
        display_columns = ['symbol', 'name', 'category', 'Close', 'ema61', 
                          'trend_status', 'dynamic_exit', 'exit_distance_pct', 'action']
        
        # 确保所有列都存在
        available_columns = [col for col in display_columns if col in df_dashboard.columns]
        
        # 格式化显示
        display_df = df_dashboard[available_columns].copy()
        
        # 格式化数字
        numeric_cols = ['Close', 'ema61', 'dynamic_exit']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.4f}" if not pd.isna(x) else "N/A")
        
        if 'exit_distance_pct' in display_df.columns:
            display_df['exit_distance_pct'] = display_df['exit_distance_pct'].apply(
                lambda x: f"{(x * 100):.2f}%" if not pd.isna(x) else "N/A")
        
        # 使用Streamlit的表格功能，而不是数据框，以获得更好的格式控制
        st.table(display_df)
        
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
                
            if df_selected is not None and not df_selected.empty:
                try:
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
                    
                    # 计算并添加EMA61线
                    ema61 = df_selected['Close'].ewm(span=61, adjust=False).mean()
                    fig.add_trace(go.Scatter(
                        x=df_selected.index,
                        y=ema61,
                        name='61日EMA',
                        line=dict(color='orange', width=2)
                    ))
                    
                    # 优化Y轴范围 - 修复错误
                    try:
                        low_min = float(df_selected['Low'].min())
                        high_max = float(df_selected['High'].max())
                        ema61_min = float(ema61.min())
                        ema61_max = float(ema61.max())
                        
                        y_min = min(low_min, ema61_min) * 0.98
                        y_max = max(high_max, ema61_max) * 1.02
                    except:
                        # 如果计算Y轴范围出错，使用默认范围
                        y_min = float(df_selected['Low'].min()) * 0.98
                        y_max = float(df_selected['High'].max()) * 1.02
                    
                    fig.update_layout(
                        title=f"{selected_item['name']} 技术分析",
                        xaxis_title='日期',
                        yaxis_title='价格',
                        xaxis_rangeslider_visible=False,
                        yaxis=dict(range=[y_min, y_max])
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 显示最新数据
                    result = calculate_technicals_simple(df_selected)
                    if result is not None:
                        cols = st.columns(4)
                        cols[0].metric("最新价", f"{result['Close']:.4f}")
                        cols[1].metric("61日EMA", f"{result['ema61']:.4f}")
                        cols[2].metric("趋势状态", result['trend_status'])
                        cols[3].metric("距止盈跌幅", f"{(result['exit_distance_pct'] * 100):.2f}%")
                except Exception as e:
                    st.error(f"绘制图表时出错: {e}")
                    import traceback
                    st.error(traceback.format_exc())
    else:
        st.warning("未能获取任何数据，请检查网络连接和代码配置")

if __name__ == "__main__":
    main()
