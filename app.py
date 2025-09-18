import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import akshare as ak
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# 设置页面
st.set_page_config(page_title="Leo DashBoard", layout="wide")
st.title("🔥 Leo TV is DB")

# 标的配置
PORTFOLIO = [
    {"category": "美股大盘", "symbol": "^IXIC", "name": "纳斯达克指数", "source": "yfinance"},
    {"category": "A股大盘", "symbol": "000001", "name": "上证指数", "source": "akshare"},
    {"category": "美股科技ETF", "symbol": "XLK", "name": "科技ETF", "source": "yfinance"},
    {"category": "美股医药ETF", "symbol": "XLV", "name": "医疗ETF", "source": "yfinance"},
    {"category": "A股科技ETF", "symbol": "516630", "name": "云计算50", "source": "akshare"},
    {"category": "A股科技ETF", "symbol": "588200", "name": "科创芯片", "source": "akshare"},
    {"category": "A股医药ETF", "symbol": "588860", "name": "科创医药", "source": "akshare"},
    {"category": "港股医药ETF", "symbol": "159892", "name": "恒生医药", "source": "akshare"},
    {"category": "港股医药ETF", "symbol": "159316", "name": "恒生创新药", "source": "akshare"},
    {"category": "港股科技ETF", "symbol": "513180", "name": "恒生科技", "source": "akshare"},
    {"category": "美股纳指ETF", "symbol": "513300", "name": "纳指ETF", "source": "akshare"},
    {"category": "黄金ETF", "symbol": "518880", "name": "黄金ETF", "source": "akshare"},
    {"category": "美股科技个股", "symbol": "NVDA", "name": "英伟达", "source": "yfinance"},
    {"category": "美股科技个股", "symbol": "TSLA", "name": "特斯拉", "source": "yfinance"},
    {"category": "港股科技个股", "symbol": "0700.HK", "name": "腾讯控股", "source": "yfinance"},
    {"category": "A股游戏个股", "symbol": "002425", "name": "ST凯文", "source": "akshare"},
    {"category": "A股机器人个股", "symbol": "000559", "name": "万向钱潮", "source": "akshare"},
    {"category": "A股算力个股", "symbol": "600654", "name": "中安科", "source": "akshare"},
    {"category": "A股医美个股", "symbol": "002004", "name": "华邦健康", "source": "akshare"},
]

# 手动调整的除权除息信息（可以预先设置已知的除权除息）
# 对于现金分红，我们需要使用不同的调整方式
DIVIDEND_ADJUSTMENTS = {
    "002004": {
        "date": "2025-09-16", 
        "dividend_per_share": 0.2,  # 每股现金分红0.2元
        "adjustment_type": "cash_dividend",  # 现金分红
        "confirmed": True
    },
}

# 检测可能的除权除息事件
def detect_dividend_events(symbol, name, df):
    """检测可能的除权除息事件"""
    events = []
    
    if df is None or len(df) < 2:
        return events
    
    try:
        # 检查最近5个交易日内的价格异常变动
        for i in range(1, min(6, len(df))):
            # 确保索引有效
            if -i-1 < -len(df) or -i < -len(df):
                continue
                
            prev_close = df['Close'].iloc[-i-1]
            current_close = df['Close'].iloc[-i]
            
            # 确保是标量值，不是Series
            if hasattr(prev_close, 'item'):
                prev_close = prev_close.item()
            if hasattr(current_close, 'item'):
                current_close = current_close.item()
                
            price_change = (current_close - prev_close) / prev_close
            
            # 如果价格变动超过阈值，可能是除权除息
            if price_change < -0.08:  # 单日跌幅超过8%
                event_date = df.index[-i].strftime('%Y-%m-%d')
                adjustment_factor = current_close / prev_close
                
                events.append({
                    "symbol": symbol,
                    "name": name,
                    "date": event_date,
                    "price_change": price_change,
                    "adjustment_factor": adjustment_factor,
                    "prev_close": prev_close,
                    "current_close": current_close
                })
    except Exception as e:
        st.error(f"检测 {name}({symbol}) 除权除息事件时出错: {e}")
    
    return events

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

# 处理除权除息调整
def adjust_for_dividends(df, symbol):
    if symbol in DIVIDEND_ADJUSTMENTS and DIVIDEND_ADJUSTMENTS[symbol].get("confirmed", False):
        adjustment = DIVIDEND_ADJUSTMENTS[symbol]
        adjustment_date = pd.to_datetime(adjustment["date"])
        
        # 找到调整日期之前的所有数据
        pre_adjustment = df[df.index < adjustment_date]
        
        if not pre_adjustment.empty:
            # 现金分红调整
            if adjustment.get("adjustment_type") == "cash_dividend" and "dividend_per_share" in adjustment:
                dividend_per_share = adjustment["dividend_per_share"]
                
                # 对于现金分红，我们需要将分红前的价格减去分红金额
                for col in ['Open', 'High', 'Low', 'Close']:
                    df.loc[df.index < adjustment_date, col] = df.loc[df.index < adjustment_date, col] - dividend_per_share
            
            # 比例调整（股票分割等）
            elif adjustment.get("adjustment_type") == "factor" and "adjustment_factor" in adjustment:
                adjustment_factor = adjustment["adjustment_factor"]
                
                # 对于比例调整，我们需要将分红前的价格乘以调整因子
                for col in ['Open', 'High', 'Low', 'Close']:
                    df.loc[df.index < adjustment_date, col] = df.loc[df.index < adjustment_date, col] * adjustment_factor
                
                # 调整成交量
                df.loc[df.index < adjustment_date, 'Volume'] = df.loc[df.index < adjustment_date, 'Volume'] / adjustment_factor
    
    return df

# 计算技术指标
def calculate_technicals_simple(df, symbol):
    if df is None or df.empty or len(df) < 65:
        return None
    
    try:
        # 处理除权除息调整
        df = adjust_for_dividends(df, symbol)
        
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
        
        # 存储调整后的数据用于后续分析
        result['adjusted_data'] = df
        
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
    dividend_events = []
    
    # 显示进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 首先收集所有可能的除权除息事件
    for i, item in enumerate(PORTFOLIO):
        status_text.text(f"正在分析 {item['name']} 的除权除息事件 ({i+1}/{len(PORTFOLIO)})")
        progress_bar.progress((i+1)/len(PORTFOLIO))
        
        try:
            # 获取数据
            if item['source'] == 'yfinance':
                df = get_data_yfinance(item['symbol'], item['name'])
            else:
                df = get_data_akshare(item['symbol'], item['name'])
            
            # 检测除权除息事件
            if df is not None and not df.empty:
                events = detect_dividend_events(item['symbol'], item['name'], df)
                dividend_events.extend(events)
        
        except Exception as e:
            st.error(f"分析 {item['name']} 时出错: {e}")
        
        # 添加短暂延迟
        time.sleep(0.1)
    
    # 显示检测到的除权除息事件供用户确认
    if dividend_events:
        st.sidebar.subheader("📋 检测到的除权除息事件")
        for event in dividend_events:
            if event["symbol"] not in DIVIDEND_ADJUSTMENTS or not DIVIDEND_ADJUSTMENTS[event["symbol"]].get("confirmed", False):
                st.sidebar.write(f"**{event['name']}({event['symbol']})**")
                st.sidebar.write(f"日期: {event['date']}, 价格变动: {event['price_change']*100:.2f}%")
                
                if st.sidebar.button(f"确认 {event['name']} 的除权除息", key=f"confirm_{event['symbol']}_{event['date']}"):
                    DIVIDEND_ADJUSTMENTS[event["symbol"]] = {
                        "date": event["date"],
                        "adjustment_factor": event["adjustment_factor"],
                        "adjustment_type": "factor",
                        "confirmed": True
                    }
                    st.sidebar.success(f"已确认 {event['name']} 的除权除息事件")
    
    # 清除进度条
    progress_bar.empty()
    status_text.empty()
    
    # 重新显示进度条进行数据处理
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
                result = calculate_technicals_simple(df, item['symbol'])
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
        st.subheader("监控仪表板")
        
        # 创建列名映射字典
        column_name_mapping = {
            'ema61': '生命线',
        }
        
        # 选择要显示的列
        display_columns = ['symbol', 'name', 'category', 'Close', 'ema61', 
                          'trend_status', 'dynamic_exit', 'exit_distance_pct', 'action']
        
        # 确保所有列都存在
        available_columns = [col for col in display_columns if col in df_dashboard.columns]
        
        # 格式化显示
        display_df = df_dashboard[available_columns].copy()
        
        # 重命名列
        display_df = display_df.rename(columns=column_name_mapping)
        
        # 格式化数字
        numeric_cols = ['Close', '生命线', 'dynamic_exit']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.4f}" if not pd.isna(x) else "N/A")
        
        if 'exit_distance_pct' in display_df.columns:
            display_df['exit_distance_pct'] = display_df['exit_distance_pct'].apply(
                lambda x: f"{(x * 100):.2f}%" if not pd.isna(x) else "N/A")
        
        # 使用Streamlit的表格功能，而不是数据框，以获得更好的格式控制
        st.table(display_df)
        
        # 添加手动调整说明
        st.info("""
        **除权除息说明**：
        - 系统会自动检测可能的除权除息事件并在侧边栏显示
        - 您可以在侧边栏确认或忽略这些事件
        - 已确认的除权除息事件会自动应用到价格计算中
        - 现金分红和股票分割使用不同的调整方式
        """)
        
        # 选择标的显示详细图表
        st.subheader("个股技术分析")
        options = [f"{item['symbol']} - {item['name']}" for item in all_data]
        selected_symbol = st.selectbox("选择标的", options)
        symbol = selected_symbol.split(' - ')[0]
        selected_item = next((item for item in all_data if item['symbol'] == symbol), None)
        
        if selected_item:
            # 使用已经计算好的调整后数据
            df_selected = selected_item.get('adjusted_data')
            
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
                    
                    # 显示最新数据 - 直接从已计算的结果中获取
                    cols = st.columns(4)
                    cols[0].metric("最新价", f"{selected_item['Close']:.4f}")
                    cols[1].metric("生命线", f"{selected_item['ema61']:.4f}")
                    cols[2].metric("趋势状态", selected_item['trend_status'])
                    cols[3].metric("距止盈跌幅", f"{(selected_item['exit_distance_pct'] * 100):.2f}%")
                    
                    # 显示调试信息
                    with st.expander("调试信息"):
                        st.write(f"数据点数: {len(df_selected)}")
                        st.write(f"最新5个收盘价: {df_selected['Close'].tail(5).tolist()}")
                        st.write(f"生命线计算值: {selected_item['ema61']:.4f}")
                        if symbol in DIVIDEND_ADJUSTMENTS:
                            st.write(f"已应用除权除息调整: {DIVIDEND_ADJUSTMENTS[symbol]}")
                except Exception as e:
                    st.error(f"绘制图表时出错: {e}")
                    import traceback
                    st.error(traceback.format_exc())
    else:
        st.warning("未能获取任何数据，请检查网络连接和代码配置")

if __name__ == "__main__":
    main()
