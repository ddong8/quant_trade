# backend/app/tasks.py
import pandas as pd
import importlib.util
from typing import Dict, Any, List, Optional
import math
from datetime import datetime

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.crud import crud_backtest, crud_strategy
from app.schemas.backtest import BacktestResultUpdate, BacktestResultCreate, KlineDuration
from app.services.data_service import data_service
from app.services.strategy_base import BaseStrategy

class SimpleBacktester:
    def __init__(self, backtest_id: int, symbol: str, duration: KlineDuration, start_date: str, end_date: str, strategy_code: str, 
                 commission_rate: float, slippage: float,
                 initial_cash: float = 100000.0, params_override: Optional[Dict] = None):
        self.backtest_id = backtest_id
        self.symbol = symbol
        self.duration = duration
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_code = strategy_code
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0
        self.total_equity = initial_cash
        self.equity_curve = []
        self.trades = []
        self.last_signal = None
        self.params_override = params_override or {}

    def _execute_strategy_code(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        try:
            spec = importlib.util.spec_from_loader("strategy_module", loader=None)
            strategy_module = importlib.util.module_from_spec(spec)
            
            # 【修复】手动注入 BaseStrategy 到策略模块的命名空间
            strategy_module.BaseStrategy = BaseStrategy
            
            exec(self.strategy_code, strategy_module.__dict__)
            
            strategy_class = strategy_module.Strategy
            strategy_instance = strategy_class(context=self, **self.params_override)
            strategy_instance.initialize()

            all_signals = []
            long_window_val = getattr(strategy_instance, 'long_window', 50)
            for i in range(long_window_val, len(data)):
                current_data = data.iloc[:i+1]
                signals = strategy_instance.handle_data(current_data)
                if signals:
                    all_signals.extend(signals)
            return all_signals
        except Exception as e:
            raise type(e)(f"Error executing strategy code: {e}. Ensure it has a 'Strategy' class inheriting from BaseStrategy.")
    
    def run(self) -> Dict[str, Any]:
        data = data_service.get_kline_data(self.symbol, self.duration, self.start_date, self.end_date)
        if data.empty:
            raise ValueError("Failed to fetch data for backtest.")

        signals = self._execute_strategy_code(data.copy())
        if signals:
            signals_df = pd.DataFrame(signals).set_index('date')
        else:
            signals_df = pd.DataFrame()
        
        for index, row in data.iterrows():
            current_price = row['close']
            trade_date = row['trade_date']
            
            if not signals_df.empty and trade_date in signals_df.index:
                signal_data = signals_df.loc[trade_date]
                signal = signal_data['signal'] if isinstance(signal_data, pd.Series) else signal_data['signal'].iloc[0]

                if signal == 'buy' and self.position == 0 and self.last_signal != 'buy':
                    buy_price = current_price + self.slippage
                    shares_to_buy = self.cash / buy_price
                    commission = shares_to_buy * buy_price * self.commission_rate
                    
                    self.position = shares_to_buy
                    self.cash -= commission
                    self.trades.append({'date': trade_date, 'type': 'buy', 'price': buy_price, 'shares': shares_to_buy})
                    self.last_signal = 'buy'

                elif signal == 'sell' and self.position > 0 and self.last_signal != 'sell':
                    sell_price = current_price - self.slippage
                    shares_sold = self.position
                    sale_value = shares_sold * sell_price
                    commission = sale_value * self.commission_rate

                    self.cash = sale_value - commission
                    self.position = 0
                    self.trades.append({'date': trade_date, 'type': 'sell', 'price': sell_price, 'shares': shares_sold})
                    self.last_signal = 'sell'
            
            self.total_equity = self.cash + self.position * current_price
            self.equity_curve.append({'date': trade_date, 'pnl': self.total_equity})

        if self.position > 0:
            self.cash = self.position * data['close'].iloc[-1]
            self.position = 0
            self.total_equity = self.cash
        return self.calculate_performance()

    def calculate_performance(self) -> Dict[str, Any]:
        if not self.equity_curve:
            return {"summary": {"error": "No trades were made or data was insufficient."}}

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        # 1. 收益率计算
        total_return = (self.total_equity / self.initial_cash - 1)
        days = (equity_df['date'].iloc[-1] - equity_df['date'].iloc[0]).days
        annual_return = ((1 + total_return) ** (365.0 / days) - 1) if days > 0 else 0
        
        # 2. 波动率和夏普比率
        equity_df['returns'] = equity_df['pnl'].pct_change().fillna(0)
        annual_volatility = equity_df['returns'].std() * (252 ** 0.5)
        sharpe_ratio = (annual_return / annual_volatility) if annual_volatility != 0 else 0

        # 3. 索提诺比率 (只考虑下行风险)
        downside_returns = equity_df['returns'][equity_df['returns'] < 0]
        downside_std = downside_returns.std() * (252 ** 0.5)
        sortino_ratio = (annual_return / downside_std) if downside_std != 0 else 0

        # 4. 最大回撤和卡玛比率
        equity_df['peak'] = equity_df['pnl'].cummax()
        equity_df['drawdown'] = (equity_df['pnl'] - equity_df['peak']) / equity_df['peak']
        max_drawdown = equity_df['drawdown'].min()
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 5. 交易统计
        num_trades = len(self.trades) // 2
        winning_trades = 0
        losing_trades = 0
        profit_factor = 0
        win_rate = 0

        if num_trades > 0:
            trade_returns = []
            for i in range(0, len(self.trades) - 1, 2):
                buy_trade = self.trades[i]
                sell_trade = self.trades[i+1]
                trade_return = (sell_trade['price'] - buy_trade['price']) / buy_trade['price']
                trade_returns.append(trade_return)
            
            wins = [r for r in trade_returns if r > 0]
            losses = [r for r in trade_returns if r <= 0]
            winning_trades = len(wins)
            losing_trades = len(losses)
            win_rate = winning_trades / num_trades if num_trades > 0 else 0
            
            total_profit = sum(wins)
            total_loss = abs(sum(losses))
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        summary = {
            "initial_equity": self.initial_cash,
            "final_equity": self.total_equity,
            "total_return": total_return,
            "annualized_return": annual_return,
            "annualized_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "max_drawdown": max_drawdown,
            "total_trades": num_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
        }
        
        return {"summary": summary, "daily_pnl": self.equity_curve, "trades": self.trades}


@celery_app.task
def run_backtest_task(backtest_id: int, params_override: Optional[Dict] = None):
    db = SessionLocal()
    backtest_record = crud_backtest.get_backtest_result(db, backtest_id)
    if not backtest_record:
        db.close()
        return

    if params_override:
        summary = backtest_record.summary or {}
        summary['params'] = params_override
        crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in={"summary": summary})
    
    crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in={"status": "RUNNING"})
    
    try:
        strategy = crud_strategy.get_strategy(db, backtest_record.strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")
        
        if not strategy.script_path:
            raise ValueError(f"Strategy '{strategy.name}' has no script path.")

        try:
            with open(strategy.script_path, 'r', encoding='utf-8') as f:
                strategy_code_content = f.read()
        except FileNotFoundError:
            raise ValueError(f"Strategy script file not found at path: {strategy.script_path}")

        start_date_formatted = backtest_record.start_dt.strftime('%Y%m%d')
        end_date_formatted = backtest_record.end_dt.strftime('%Y%m%d')

        backtester = SimpleBacktester(
            backtest_id=backtest_id,
            symbol=backtest_record.symbol,
            duration=backtest_record.duration,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            strategy_code=strategy_code_content,
            commission_rate=backtest_record.commission_rate,
            slippage=backtest_record.slippage,
            params_override=params_override
        )
        
        result = backtester.run()
        
        daily_pnl_with_trades = {
            "pnl": result.get("daily_pnl", []),
            "trades": result.get("trades", [])
        }

        final_summary = backtest_record.summary or {}
        final_summary.update(result["summary"])

        update_data = BacktestResultUpdate(
            status="SUCCESS",
            summary=final_summary,
            daily_pnl=daily_pnl_with_trades
        )
        crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in=update_data)

    except Exception as e:
        import traceback
        traceback.print_exc() # 打印完整的错误堆栈
        error_summary = backtest_record.summary or {}
        error_summary["error"] = str(e)
        update_data = BacktestResultUpdate(status="FAILURE", summary=error_summary)
        crud_backtest.update_backtest_result(db, db_obj=backtest_record, obj_in=update_data)
    finally:
        db.close()

@celery_app.task
def run_optimization_task(
    strategy_id: int,
    backtest_params: dict,
    optimization_params: List[Dict[str, Any]],
    optimization_id: str
):
    import numpy as np
    from itertools import product

    param_ranges = []
    param_names = []
    for p in optimization_params:
        param_names.append(p['name'])
        param_ranges.append(np.arange(p['start'], p['end'] + p['step'], p['step']))

    param_combinations = list(product(*param_ranges))
    
    print(f"Starting optimization {optimization_id} for strategy {strategy_id} with {len(param_combinations)} combinations.")
    
    db = SessionLocal()
    try:
        # 【修正】: 将 backtest_params 中的字符串转回对象
        params_for_db = {
            "symbol": backtest_params['symbol'],
            "duration": KlineDuration(backtest_params['duration']),
            "start_dt": datetime.fromisoformat(backtest_params['start_dt_iso']),
            "end_dt": datetime.fromisoformat(backtest_params['end_dt_iso']),
            "commission_rate": backtest_params['commission_rate'],
            "slippage": backtest_params['slippage'],
        }
        
        for combo in param_combinations:
            param_set = {name: round(val, 2) for name, val in zip(param_names, combo)}
            print(f"Dispatching backtest for parameters: {param_set}")
            
            backtest_create = BacktestResultCreate(
                strategy_id=strategy_id,
                optimization_id=optimization_id,
                **params_for_db
            )
            db_backtest = crud_backtest.create_backtest_result(db, obj_in=backtest_create)
            run_backtest_task.delay(db_backtest.id, params_override=param_set)
    finally:
        db.close()
    
    print(f"Optimization {optimization_id} finished dispatching all tasks.")