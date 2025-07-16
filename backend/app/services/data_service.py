# backend/app/services/data_service.py
import pandas as pd
import asyncio
from tqsdk import TqApi, TqAuth
from datetime import datetime
from app.schemas.backtest import KlineDuration
from app.core.config import TQ_USER, TQ_PASSWORD

class DataService:
    async def _fetch_data_async(self, symbol: str, duration_seconds: int, data_length: int) -> pd.DataFrame:
        """
        一个独立的、纯异步的函数，负责所有与TqSdk的交互。
        """
        api = None
        try:
            # 在异步函数内部创建和关闭TqApi
            api = TqApi(auth=TqAuth(TQ_USER, TQ_PASSWORD))
            print(f"Async fetch: Requesting {data_length} klines for symbol {symbol}...")
            klines = api.get_kline_serial(symbol, duration_seconds=duration_seconds, data_length=data_length)
            
            # 等待数据加载完成
            # 设置一个超时以防万一
            wait_deadline = datetime.now().timestamp() + 60  # 增加超时到60秒
            while not api.is_preloaded(klines):
                # 使用 asyncio.sleep 让出控制权，让TqSdk的后台任务有机会运行
                await asyncio.sleep(0.1)
                if datetime.now().timestamp() > wait_deadline:
                    raise Exception("TqSdk preloading klines timed out after 60 seconds.")

            print(f"Async fetch: Klines preloaded. Total rows received: {len(klines)}")
            return pd.DataFrame(klines)
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            if api:
                api.close()

    def get_kline_data(self, symbol: str, duration: KlineDuration, start_date: str, end_date: str) -> pd.DataFrame:
        """
        同步的入口函数，它调用并运行异步的 fetching 函数。
        """
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
            
            days = (end_dt - start_dt).days
            if days <= 0:
                days = 1
            
            if duration_seconds >= 24 * 60 * 60:
                data_length = int(days * 1.5) + 200 
            else:
                trading_hours_per_day = 8 
                bars_per_hour = 3600 / duration_seconds
                data_length = int(days * trading_hours_per_day * bars_per_hour * 1.5) + 500
            
            # 使用 asyncio.run() 来同步地执行异步函数
            # 这会创建一个新的事件循环，运行任务，然后关闭循环。
            klines_df = asyncio.run(self._fetch_data_async(symbol, duration_seconds, data_length))

            if klines_df.empty:
                return pd.DataFrame()

            klines_df['datetime_dt'] = pd.to_datetime(klines_df['datetime'], unit='ns')

            klines_filtered = klines_df[
                (klines_df['datetime_dt'].dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.date >= start_dt.date()) &
                (klines_df['datetime_dt'].dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.date <= end_dt.date())
            ]
            
            print(f"Rows after filtering by date range: {len(klines_filtered)}")

            if klines_filtered.empty:
                return pd.DataFrame()

            klines_final = klines_filtered.copy()
            klines_final.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'vol'
            }, inplace=True)
            klines_final['trade_date'] = klines_final['datetime_dt'].dt.strftime('%Y%m%d %H:%M:%S')
            
            return klines_final[['trade_date', 'open', 'high', 'low', 'close', 'vol']].reset_index(drop=True)
            
        except Exception as e:
            print(f"Error in get_kline_data for {symbol}: {e}")
            return pd.DataFrame()

data_service = DataService()

if __name__ == '__main__':
    try:
        # 测试获取螺纹钢2501合约 3个月的日线数据
        print("--- Testing Daily Data ---")
        test_data_daily = data_service.get_kline_data('SHFE.rb2501', KlineDuration.one_day, '20240101', '20240331')
        if not test_data_daily.empty:
            print("\nSuccessfully fetched Daily data:")
            print(test_data_daily.head())
            print(test_data_daily.tail())
            print(f"Total rows: {len(test_data_daily)}")
        else:
            print("\nFailed to fetch Daily data.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")