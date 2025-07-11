# backend/app/services/backtester.py
import pandas as pd
from app.services.data_service import data_service
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.schemas.backtest import KlineDuration, BacktestResultCreate
from app.crud import crud_backtest

class SimpleBacktester:
    def __init__(self, symbol: str, duration: KlineDuration, start_date: str, end_date: str, strategy_code: str, initial_cash: float = 100000.0):
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

    def _execute_strategy_code(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Dynamically execute user-provided strategy code.
        The code must contain a function `run_strategy(data: pd.DataFrame) -> list`.
        """
        try:
            # Create a namespace for the execution
            namespace = {'pd': pd}
            # Execute the strategy code
            exec(self.strategy_code, namespace)
            
            # Get the strategy function from the namespace
            strategy_func = namespace.get('run_strategy')
            if not callable(strategy_func):
                raise ValueError("Strategy code must contain a callable function named 'run_strategy'.")
            
            # Run the strategy function and get signals
            signals = strategy_func(data)
            return signals
        except Exception as e:
            raise type(e)(f"Error executing strategy code: {e}")

    def run(self) -> Dict[str, Any]:
        """
        Run the backtest and return the results.
        """
        # 1. Get data
        data = data_service.get_kline_data(self.symbol, self.duration, self.start_date, self.end_date)
        if data.empty:
            raise ValueError("Failed to fetch data for backtest.")

        # 2. Get signals from the user's strategy code
        signals = self._execute_strategy_code(data.copy())
        signals_df = pd.DataFrame(signals).set_index('date')
        
        # 3. Iterate through data and apply signals
        for index, row in data.iterrows():
            current_price = row['close']
            trade_date = row['trade_date']
            
            if trade_date in signals_df.index:
                signal = signals_df.loc[trade_date, 'signal']
                if signal == 'buy' and self.position == 0:
                    # Buy
                    shares_to_buy = self.cash / current_price
                    self.position = shares_to_buy
                    self.cash = 0
                elif signal == 'sell' and self.position > 0:
                    # Sell
                    self.cash = self.position * current_price
                    self.position = 0
            
            # Update daily equity
            self.total_equity = self.cash + self.position * current_price
            self.equity_curve.append({'date': trade_date, 'pnl': self.total_equity})

        # 4. Calculate performance metrics
        return self.calculate_performance()

    def calculate_performance(self) -> Dict[str, Any]:
        """
        Calculate various performance metrics for the backtest.
        """
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
        
        result = {
            "summary": summary,
            "daily_pnl": self.equity_curve
        }
        return result

def run_backtest_for_strategy(db: Session, strategy_id: int, strategy_code: str, symbol: str, duration: KlineDuration, start_dt: str, end_dt: str) -> Dict[str, Any]:
    """
    Entry point for running a backtest for a specific strategy.
    """
    start_date_formatted = pd.to_datetime(start_dt).strftime('%Y%m%d')
    end_date_formatted = pd.to_datetime(end_dt).strftime('%Y%m%d')

    try:
        backtester = SimpleBacktester(symbol, duration, start_date_formatted, end_date_formatted, strategy_code)
        result = backtester.run()
        result['strategy_id'] = strategy_id
        
        # Save result to DB
        if "error" not in result["summary"]:
            result_to_save = BacktestResultCreate(
                strategy_id=strategy_id,
                summary=result["summary"],
                daily_pnl=result["daily_pnl"]
            )
            crud_backtest.create_backtest_result(db, obj_in=result_to_save)

        return result
    except Exception as e:
        print(f"Backtest failed for strategy {strategy_id}: {e}")
        return {"strategy_id": strategy_id, "summary": {"error": str(e)}}

