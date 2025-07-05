import asyncio
import random
import time
import threading
from app.services.websocket_manager import manager

# 用一个字典来管理正在运行的策略
strategy_runners = {}

class MockStrategyRunner:
    def __init__(self, strategy_id: int):
        self.strategy_id = strategy_id
        self._is_running = False
        self.thread = None
        self.pnl = 0.0

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print(f"Strategy {self.strategy_id} runner started.")

    def stop(self):
        self._is_running = False
        if self.thread:
            self.thread.join(timeout=2) # 等待线程结束
        print(f"Strategy {self.strategy_id} runner stopped.")

    def run(self):
        """模拟策略运行的主循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._is_running:
            try:
                # 1. 模拟P&L变化
                self.pnl += random.uniform(-150.5, 200.5)
                pnl_update = {
                    "type": "pnl_update",
                    "data": {"pnl": round(self.pnl, 2), "timestamp": time.time()}
                }
                asyncio.run(manager.broadcast(pnl_update))

                # 2. 模拟日志输出
                if random.random() < 0.3: # 30%的概率产生日志
                    log_message = {
                        "type": "log",
                        "data": {"strategy_id": self.strategy_id, "message": f"Signal detected. Current PnL: {self.pnl:.2f}"}
                    }
                    asyncio.run(manager.broadcast(log_message))

                time.sleep(random.uniform(2, 5)) # 模拟TqSDK的wait_update()
            except Exception as e:
                print(f"Error in mock runner for strategy {self.strategy_id}: {e}")
        
        # 线程结束前，发送最终状态
        final_log = {
            "type": "log",
            "data": {"strategy_id": self.strategy_id, "message": "Strategy has stopped."}
        }
        asyncio.run(manager.broadcast(final_log))


def start_strategy_runner(strategy_id: int):
    if strategy_id in strategy_runners:
        strategy_runners[strategy_id].stop()
    
    runner = MockStrategyRunner(strategy_id)
    strategy_runners[strategy_id] = runner
    runner.start()
    return runner

def stop_strategy_runner(strategy_id: int):
    if strategy_id in strategy_runners:
        strategy_runners[strategy_id].stop()
        del strategy_runners[strategy_id]
        return True
    return False