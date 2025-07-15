# backend/app/services/data_service.py
import pandas as pd
from tqsdk import TqApi, TqAuth
from datetime import datetime
from app.schemas.backtest import KlineDuration
from app.core.config import TQ_USER, TQ_PASSWORD

class DataService:
    def get_kline_data(self, symbol: str, duration: KlineDuration, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指定期货合约在日期范围内的K线行情数据
        :param symbol: TqSdk的合约代码, e.g., 'SHFE.rb2501'
        :param duration: K线周期, KlineDuration枚举类型
        :param start_date: 开始日期, 格式 'YYYYMMDD'
        :param end_date: 结束日期, 格式 'YYYYMMDD'
        :return: pandas DataFrame, 包含开高低收等数据
        """
        # 在函数内部创建和关闭TqApi实例，确保线程安全
        api = TqApi(auth=TqAuth(TQ_USER, TQ_PASSWORD))
        try:
            duration_map = {
                "1d": 24 * 60 * 60,
                "1h": 60 * 60,
                "15m": 15 * 60,
                "5m": 5 * 60,
                "1m": 1 * 60,
            }
            duration_seconds = duration_map[duration.value]

            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            # 根据周期估算数据长度
            days = (end_dt - start_dt).days
            if duration_seconds >= 24 * 60 * 60:
                data_length = int(days * 1.2) + 50 # 日线
            else:
                data_length = int(days * (24 * 60 * 60 / duration_seconds) * 1.2) + 200 # 分钟线
            
            klines = api.get_kline_serial(symbol, duration_seconds=duration_seconds, data_length=data_length)

            # TqSdk返回的是纳秒级时间戳，需要转换为datetime对象
            klines['datetime'] = pd.to_datetime(klines['datetime'], unit='ns')

            klines = klines[klines.datetime.dt.date >= start_dt.date()]
            klines = klines[klines.datetime.dt.date <= end_dt.date()]
            
            if klines.empty:
                return pd.DataFrame()

            klines = klines.rename(columns={
                'datetime': 'trade_date_dt',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'vol'
            })
            klines['trade_date'] = klines['trade_date_dt'].dt.strftime('%Y%m%d %H:%M:%S')
            
            return klines[['trade_date', 'open', 'high', 'low', 'close', 'vol']].reset_index(drop=True)
            
        except Exception as e:
            print(f"Error fetching data from TqSdk for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            # 确保api被关闭
            api.close()



data_service = DataService()

if __name__ == '__main__':
    try:
        # 测试获取螺纹钢2501合约2024年6月的1小时K线
        test_data = data_service.get_kline_data('SHFE.rb2501', KlineDuration.one_hour, '20240601', '20240630')
        if not test_data.empty:
            print("Successfully fetched 1H data:")
            print(test_data.head())
        else:
            print("Failed to fetch 1H data.")
            
        # 测试获取日线
        test_data_daily = data_service.get_kline_data('SHFE.rb2501', KlineDuration.one_day, '20240601', '20240630')
        if not test_data_daily.empty:
            print("Successfully fetched Daily data:")
            print(test_data_daily.head())
        else:
            print("Failed to fetch Daily data.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")