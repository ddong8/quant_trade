# backend/app/tasks.py
import pandas as pd
import redis
import json
from typing import Dict, Any, List

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.crud import crud_backtest, crud_strategy
from app.schemas.backtest import BacktestResultUpdate
from app.services.data_service import data_service
from app.core.config import CELERY_BROKER_URL

# We move the backtester logic here to make the task self-contained.
class SimpleBacktester:
    def __init__(self, backtest_id: int, symbol: str, duration: str, start_date: str, end_date: str, strategy_code: str, initial_cash: float = 100000.0):
        self.backtest_id = backtest_id
        self.symbol = symbol
        self.duration = duration
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_code = strategy_code
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0
        self.total_equity = initial_cash
        self.equity_curve = []
        self.redis_client = redis.from_url(CELERY_BROKER_URL)

    def _publish_event(self, event_type: str, data: Dict[str, Any]):
        channel = f"backtest_{self.backtest_id}"
        message = json.dumps({"type": event_type, "data": data})
        print(f"--- TASK: Publishing to Redis channel '{channel}': {message} ---")
        self.redis_client.publish(channel, message)

    def _execute_strategy_code(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        try:
            namespace = {'pd': pd}
            exec(self.strategy_code, namespace)
            strategy_func = namespace.get('run_strategy')
            if not callable(strategy_func):
                raise ValueError("Strategy code must contain a callable function named 'run_strategy'.")
            signals = strategy_func(data)
            return signals
        except Exception as e:
            raise type(e)(f"Error executing strategy code: {e}")

    def run(self) -> Dict[str, Any]:
        data = data_service.get_kline_data(self.symbol, self.duration, self.start_date, self.end_date)
        if data.empty:
            raise ValueError("Failed to fetch data for backtest.")

        signals = self._execute_strategy_code(data.copy())
        signals_df = pd.DataFrame(signals).set_index('date')
        
        for index, row in data.iterrows():
            current_price = row['close']
            trade_date = row['trade_date']
            
            if trade_date in signals_df.index:
                signal = signals_df.loc[trade_date, 'signal']
                if signal == 'buy' and self.position == 0:
                    shares_to_buy = self.cash / current_price
                    self.position = shares_to_buy
                    self.cash = 0
                    self._publish_event('order_event', {'date': trade_date, 'signal': 'buy', 'price': current_price, 'shares': shares_to_buy})
                elif signal == 'sell' and self.position > 0:
                    self.cash = self.position * current_price
                    self.position = 0
                    self._publish_event('order_event', {'date': trade_date, 'signal': 'sell', 'price': current_price, 'shares': self.position})
            
            self.total_equity = self.cash + self.position * current_price
            self.equity_curve.append({'date': trade_date, 'pnl': self.total_equity})
            self._publish_event('pnl_update', {'date': trade_date, 'pnl': self.total_equity})

        return self.calculate_performance()

    def calculate_performance(self) -> Dict[str, Any]:
        if not self.equity_curve:
            return {"summary": {"error": "No trades were made or data was insufficient."}}

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        total_return = (self.total_equity / self.initial_cash - 1)
        
        days = (equity_df['date'].iloc[-1] - equity_df['date'].iloc[0]).days
        annual_return = ((1 + total_return) ** (365.0 / days) - 1) if days > 0 else 0
        
        equity_df['returns'] = equity_df['pnl'].pct_change().fillna(0)
        sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * (252 ** 0.5) if equity_df['returns'].std() != 0 else 0

        equity_df['peak'] = equity_df['pnl'].cummax()
        equity_df['drawdown'] = (equity_df['pnl'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()

        summary = {
            "total_return": total_return,
            "annualized_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "final_equity": self.total_equity,
            "initial_equity": self.initial_cash,
        }
        
        return {"summary": summary, "daily_pnl": self.equity_curve}


@celery_app.task
def run_backtest_task(backtest_id: int):
    db = SessionLocal()
    backtest_record = crud_backtest.get_backtest_result(db, backtest_id)
    if not backtest_record:
        db.close()
        return

    # Update status to RUNNING
    crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in={"status": "RUNNING"})

    try:
        strategy = crud_strategy.get_strategy(db, backtest_record.strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")

        start_date_formatted = backtest_record.start_dt.strftime('%Y%m%d')
        end_date_formatted = backtest_record.end_dt.strftime('%Y%m%d')

        backtester = SimpleBacktester(
            backtest_id=backtest_id,
            symbol=backtest_record.symbol,
            duration=backtest_record.duration.value,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            strategy_code=strategy.content
        )
        
        result = backtester.run()

        update_data = BacktestResultUpdate(
            status="SUCCESS",
            summary=result["summary"],
            daily_pnl=result["daily_pnl"]
        )
        crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in=update_data)

    except Exception as e:
        # On failure, update status and save the error message
        error_summary = {"error": str(e)}
        update_data = BacktestResultUpdate(status="FAILURE", summary=error_summary)
        crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in=update_data)
    finally:
        db.close()
