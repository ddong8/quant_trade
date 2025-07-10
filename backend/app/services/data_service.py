# backend/app/services/data_service.py
import pandas as pd
from tqsdk import TqApi, TqAuth
from datetime import datetime, timedelta

class DataService:
    def __init__(self):
        # 初始化TqApi用于数据服务，不连接交易账户
        # web_gui=True在后台运行时可以避免一些问题
        self.api = TqApi(web_gui=True, auth=TqAuth("ddong8", "dhx.520"))
        print("TqSdk Data Service initialized successfully.")

    def get_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指定期货合约在日期范围内的日线行情数据
        :param symbol: TqSdk的合约代码, e.g., 'SHFE.rb2501'
        :param start_date: 开始日期, 格式 'YYYYMMDD'
        :param end_date: 结束日期, 格式 'YYYYMMDD'
        :return: pandas DataFrame, 包含开高低收等数据
        """
        try:
            # TqSdk的get_kline_serial需要datetime对象
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            # 获取日线数据
            # data_length需要一个大概的估算值，我们估算交易日数
            days = (end_dt - start_dt).days
            data_length = int(days * 252 / 365) + 50 # 加上一些富余量
            
            klines = self.api.get_kline_serial(symbol, duration_seconds=24*60*60, data_length=data_length)

            # 筛选在指定日期范围内的数据
            klines = klines[klines.datetime.dt.date >= start_dt.date()]
            klines = klines[klines.datetime.dt.date <= end_dt.date()]
            
            if klines.empty:
                return pd.DataFrame()

            # 调整列名以兼容回测引擎
            klines = klines.rename(columns={
                'datetime': 'trade_date_dt',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'vol'
            })
            # 将datetime转换为YYYYMMDD格式的字符串
            klines['trade_date'] = klines['trade_date_dt'].dt.strftime('%Y%m%d')
            
            return klines[['trade_date', 'open', 'high', 'low', 'close', 'vol']].reset_index(drop=True)
            
        except Exception as e:
            print(f"Error fetching data from TqSdk for {symbol}: {e}")
            return pd.DataFrame()
        
    def __del__(self):
        # 在对象销毁时关闭TqApi连接
        self.api.close()

# 创建一个单例
data_service = DataService()

# 使用示例
if __name__ == '__main__':
    # 测试代码
    try:
        # 测试获取螺纹钢2510合约2025年5—7月的数据
        test_data = data_service.get_daily_data('SHFE.rb2510', '20250401', '20250709')
        if not test_data.empty:
            print("Successfully fetched data:")
            print(test_data.head())
        else:
            print("Failed to fetch data or no data available for the period.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
