# backend/app/services/data_fetcher.py
import sys
import json
import pandas as pd
from tqsdk import TqApi, TqAuth
from datetime import datetime
import argparse

# 再次简化，完全移除asyncio，使用tqsdk的纯同步阻塞模式
from app.core.config import TQ_USER, TQ_PASSWORD

def main():
    parser = argparse.ArgumentParser(description="TQSDK Data Fetcher")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--duration", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    api = None
    try:
        duration_map = {
            "1d": 24 * 60 * 60, "1h": 60 * 60, "15m": 15 * 60,
            "5m": 5 * 60, "1m": 1 * 60,
        }
        duration_seconds = duration_map[args.duration]
        start_dt = datetime.strptime(args.start, '%Y%m%d')
        end_dt = datetime.strptime(args.end, '%Y%m%d')

        # 在普通线程中创建TqApi，它会自动进入同步阻塞模式
        # disable_print=True 会禁止打印免责声明，确保stdout输出纯净的JSON
        api = TqApi(auth=TqAuth(TQ_USER, TQ_PASSWORD), disable_print=True)

        # 计算所需数据长度
        days = (end_dt - start_dt).days
        if days <= 0: days = 1
        if duration_seconds >= 24 * 60 * 60:
            data_length = int(days * 1.5) + 200
        else:
            trading_hours_per_day = 8
            bars_per_hour = 3600 / duration_seconds
            data_length = int(days * trading_hours_per_day * bars_per_hour * 1.5) + 500

        # get_kline_serial 在同步模式下会阻塞，直到数据下载完成
        klines = api.get_kline_serial(
            args.symbol,
            duration_seconds=duration_seconds,
            data_length=data_length
        )

        # 过滤日期范围
        klines_df = pd.DataFrame(klines)
        klines_df['datetime_dt'] = pd.to_datetime(klines_df['datetime'], unit='ns')
        klines_filtered = klines_df[
            (klines_df['datetime_dt'].dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.date >= start_dt.date()) &
            (klines_df['datetime_dt'].dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai').dt.date <= end_dt.date())
        ]

        if klines_filtered.empty:
            print(json.dumps([]))
            return

        # 转换datetime对象以便JSON序列化
        klines_filtered['datetime'] = klines_filtered['datetime_dt'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        klines_filtered = klines_filtered.drop(columns=['datetime_dt'])

        print(klines_filtered.to_json(orient='records'))

    except Exception as e:
        print(f"Data fetcher failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    finally:
        if api:
            api.close()

if __name__ == "__main__":
    main()
