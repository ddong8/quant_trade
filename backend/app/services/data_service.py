# backend/app/services/data_service.py
import pandas as pd
import json
import subprocess
import sys
from datetime import datetime
from app.schemas.backtest import KlineDuration

class DataService:
    def get_kline_data(self, symbol: str, duration: KlineDuration, start_date: str, end_date: str) -> pd.DataFrame:
        """
        通过调用一个独立的子进程来获取K线数据，以隔离tqsdk。
        """
        try:
            # 构建要执行的命令
            command = [
                sys.executable,  # 使用当前环境的python解释器
                "-m", "app.services.data_fetcher", # 作为模块运行
                "--symbol", symbol,
                "--duration", duration.value,
                "--start", start_date,
                "--end", end_date,
            ]

            print(f"DataService: Running subprocess with command: {' '.join(command)}")

            # 执行子进程
            # capture_output=True 会捕获stdout和stderr
            # text=True 会将输出解码为文本
            # check=True 如果返回非零状态码，会抛出CalledProcessError
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )

            # 从stdout加载JSON数据
            json_output = result.stdout
            if not json_output:
                print("Warning: Data fetcher returned empty output.")
                return pd.DataFrame()

            data = json.loads(json_output)
            if not data:
                return pd.DataFrame()

            klines_df = pd.DataFrame(data)
            
            # --- 数据格式化处理 (与之前相同) ---
            # tqsdk download_data 返回的 datetime 是字符串，需要转换
            klines_df['datetime_dt'] = pd.to_datetime(klines_df['datetime'])

            klines_final = klines_df.copy()
            klines_final.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'vol'
            }, inplace=True)
            klines_final['trade_date'] = klines_final['datetime_dt'].dt.strftime('%Y%m%d %H:%M:%S')
            
            return klines_final[['trade_date', 'open', 'high', 'low', 'close', 'vol']].reset_index(drop=True)

        except subprocess.CalledProcessError as e:
            # 如果子进程失败，打印它的stderr
            print(f"!!! FATAL ERROR in DataService subprocess !!!")
            print(f"Return code: {e.returncode}")
            print(f"Stderr: {e.stderr}")
            return pd.DataFrame()
        except Exception as e:
            import traceback
            print(f"!!! FATAL ERROR in DataService.get_kline_data !!!")
            traceback.print_exc()
            return pd.DataFrame()

data_service = DataService()

