import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from sqlalchemy.orm import Session

from app.services.backtester import SimpleBacktester, run_backtest_for_strategy
from app.schemas.backtest import KlineDuration, BacktestResultCreate

# A simple strategy for testing
TEST_STRATEGY_CODE = """
import pandas as pd

def run_strategy(data: pd.DataFrame):
    signals = []
    if len(data) > 1:
        if data['close'].iloc[-1] > data['close'].iloc[-2]:
            signals.append({'date': data.index[-1], 'signal': 'buy'})
        else:
            signals.append({'date': data.index[-1], 'signal': 'sell'})
    return signals
"""

@pytest.fixture
def mock_data_service():
    with patch('app.services.backtester.data_service') as mock:
        # Create a sample DataFrame for testing
        dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'])
        mock_data = pd.DataFrame({
            'trade_date': dates.strftime('%Y%m%d'),
            'close': [100, 110, 105, 115]
        })
        mock_data = mock_data.set_index(dates)
        mock.get_kline_data.return_value = mock_data
        yield mock

def test_simple_backtester_run(mock_data_service):
    """Test the SimpleBacktester run method."""
    backtester = SimpleBacktester(
        symbol='test.symbol',
        duration=KlineDuration.one_day,
        start_date='20230101',
        end_date='20230104',
        strategy_code=TEST_STRATEGY_CODE
    )
    result = backtester.run()

    assert 'summary' in result
    assert 'daily_pnl' in result
    assert len(result['daily_pnl']) == 4
    assert result['summary']['final_equity'] > 0

def test_run_backtest_for_strategy(mock_data_service):
    """Test the main backtest runner function."""
    mock_db = MagicMock(spec=Session)
    
    with patch('app.crud.crud_backtest.create_backtest_result') as mock_create_backtest:
        result = run_backtest_for_strategy(
            db=mock_db,
            strategy_id=1,
            strategy_code=TEST_STRATEGY_CODE,
            symbol='test.symbol',
            duration=KlineDuration.one_day,
            start_dt='2023-01-01T00:00:00',
            end_dt='2023-01-04T00:00:00'
        )

        assert result['strategy_id'] == 1
        assert 'summary' in result
        assert 'error' not in result['summary']
        mock_create_backtest.assert_called_once()
        
        # Check the type of the argument passed to create_backtest_result
        call_args = mock_create_backtest.call_args[1]
        assert 'obj_in' in call_args
        assert isinstance(call_args['obj_in'], BacktestResultCreate)
