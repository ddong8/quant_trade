# backend/app/services/live_runner.py

import asyncio
import threading
import importlib.util
from datetime import datetime
import time
import pandas as pd
import pytz
import math # 导入 math 库

from tqsdk import TqApi, TqAuth, TqSim
from tqsdk.objs import Quote

from app.core.config import TQ_USER, TQ_PASSWORD
from app.services.websocket_manager import manager

LIVE_RUNNERS = {}
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class LiveContext:
    def __init__(self, api: TqApi, strategy_instance: any, main_loop: asyncio.AbstractEventLoop):
        self._api = api
        self.strategy = strategy_instance
        self.symbol = self.strategy.symbol
        self._main_loop = main_loop

    def get_quote(self):
        return self._api.get_quote(self.symbol)
    
    def get_position(self, symbol=None):
        return self._api.get_position(symbol or self.symbol)

    def buy_open(self, symbol, volume):
        return self._api.insert_order(symbol, direction="BUY", offset="OPEN", volume=volume)

    def sell_close(self, symbol, volume):
        return self._api.insert_order(symbol, direction="SELL", offset="CLOSE", volume=volume)

    def _schedule_broadcast(self, message: dict):
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), self._main_loop)

    def broadcast(self, event_type: str, data: dict):
        message = {"type": event_type, "data": data}
        self._schedule_broadcast(message)
    
    def log(self, message: str):
        log_data = {
            "strategy_id": self.strategy.strategy_id,
            "timestamp": datetime.now(BEIJING_TZ).isoformat(),
            "message": message
        }
        self.broadcast("log", log_data)

class LiveRunner:
    def __init__(self, strategy_id: int, strategy_code: str, main_loop: asyncio.AbstractEventLoop):
        self.strategy_id = strategy_id
        self.strategy_code = strategy_code
        self._main_loop = main_loop
        self._is_running = False
        self.thread = None
        self.api = None
        self.strategy_instance = None
        self.context = None

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"LiveRunner for strategy {self.strategy_id} started.")

    def stop(self):
        self._is_running = False 
        print(f"Stop signal sent to LiveRunner for strategy {self.strategy_id}. The runner will shut down shortly.")

    def _load_strategy(self):
        try:
            spec = importlib.util.spec_from_loader(f"strategy_module_{self.strategy_id}", loader=None)
            strategy_module = importlib.util.module_from_spec(spec)
            exec(self.strategy_code, strategy_module.__dict__)
            
            StrategyClass = strategy_module.Strategy
            StrategyClass.strategy_id = self.strategy_id 
            
            self.strategy_instance = StrategyClass(context=None)
            self.strategy_instance.initialize()
            
            self.context = LiveContext(self.api, self.strategy_instance, self._main_loop)
            self.strategy_instance.context = self.context

            self.context.log(f"Strategy for '{self.strategy_instance.symbol}' initialized.")
        except Exception as e:
            print(f"Error loading strategy {self.strategy_id}: {e}")
            log_data = { "type": "log", "data": { "strategy_id": self.strategy_id, "timestamp": datetime.now(BEIJING_TZ).isoformat(), "message": f"Error loading strategy: {e}" } }
            self._main_loop.call_soon_threadsafe(self.context._schedule_broadcast, log_data)
            self._is_running = False

    def _run_loop(self):
        self.api = TqApi(TqSim(), auth=TqAuth(TQ_USER, TQ_PASSWORD))
        self._load_strategy()
        if not self._is_running:
            self.api.close()
            return
            
        symbol = self.strategy_instance.symbol
        long_window = getattr(self.strategy_instance, 'long_window', 60)
        
        klines = self.api.get_kline_serial(symbol, duration_seconds=60, data_length=long_window + 5)
        account = self.api.get_account()
        position = self.context.get_position()
        quote = self.context.get_quote()
        self.context.log("Waiting for market data...")

        last_push_time = 0
        push_interval = 3

        while self._is_running:
            try:
                self.api.wait_update(deadline=time.time() + 1)
                
                current_time = time.time()
                
                if self.api.is_changing(account) or self.api.is_changing(position) or current_time - last_push_time > push_interval:
                    account_info = { "equity": account.balance, "available": account.available }
                    
                    open_price = getattr(position, 'open_price_long', 0.0)
                    if math.isnan(open_price):
                        open_price = 0.0

                    position_info = {
                        "symbol": symbol,
                        "volume": getattr(position, 'pos_long', 0),
                        "average_price": open_price
                    }
                    update_data = { "account": account_info, "position": position_info }
                    self.context.broadcast("live_update", update_data)
                    last_push_time = current_time

                if self.api.is_changing(quote, "last_price"):
                    self.context.log(f"Tick received. Last price: {quote.last_price}")

                if self.api.is_changing(klines.iloc[-1], "datetime"):
                    df_klines = pd.DataFrame(klines)
                    df_klines.rename(columns={'vol': 'volume'}, inplace=True)
                    df_klines['trade_date'] = df_klines['datetime'].apply(lambda x: datetime.fromtimestamp(x / 1e9).strftime('%Y%m%d %H:%M:%S'))
                    
                    self.context.log(f"New 1-min K-line received. Running handle_data...")
                    signals = self.strategy_instance.handle_data(df_klines)
                    if signals:
                        for signal in signals:
                             current_position = self.context.get_position()
                             if signal['signal'] == 'buy' and not current_position.pos_long:
                                 order = self.context.buy_open(self.context.symbol, 1)
                                 self.context.log(f"BUY OPEN signal. Order sent: {order.order_id}")
                             elif signal['signal'] == 'sell' and current_position.pos_long > 0:
                                 order = self.context.sell_close(self.context.symbol, current_position.pos_long)
                                 self.context.log(f"SELL CLOSE signal. Order sent: {order.order_id}")
            except Exception as e:
                error_msg = f"Error in strategy loop {self.strategy_id}: {e}"
                print(error_msg)
                if self.context:
                    self.context.log(error_msg)
                self._is_running = False
        
        if self.context:
            self.context.log("Strategy has stopped.")
        self.api.close()
        print(f"LiveRunner for strategy {self.strategy_id} has properly shut down.")

def start_live_runner(strategy_id: int, strategy_code: str, loop: asyncio.AbstractEventLoop):
    if strategy_id in LIVE_RUNNERS:
        LIVE_RUNNERS[strategy_id].stop()
    
    runner = LiveRunner(strategy_id, strategy_code, loop)
    LIVE_RUNNERS[strategy_id] = runner
    runner.start()
    return runner

def stop_live_runner(strategy_id: int):
    if strategy_id in LIVE_RUNNERS:
        LIVE_RUNNERS[strategy_id].stop()
        del LIVE_RUNNERS[strategy_id]
        return True
    return False