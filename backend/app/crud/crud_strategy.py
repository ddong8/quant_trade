# backend/app/crud/crud_strategy.py
from sqlalchemy.orm import Session, joinedload
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate
import uuid
from pathlib import Path

# --- STRATEGY TEMPLATES ---
MA_CROSSOVER_TEMPLATE = """import pandas as pd
from app.services.strategy_base import BaseStrategy

class Strategy(BaseStrategy):
    def set_parameters(self):
        # 在这里声明所有可优化的参数及其默认值
        self.short_window = 20
        self.long_window = 50

    def initialize(self):
        self.symbol = "SHFE.rb2501"  # 交易的合约

    def handle_data(self, data: pd.DataFrame):
        '''
        Args:
            data: 一个包含最新K线数据的 pandas DataFrame。
                  在我们的回测器中，它包含所有历��数据。
                  在实盘中，它可能只包含最近的N条数据。
        '''
        # --- 信号生成 ---
        signals = []
        
        # 计算移动平均线
        short_mavg = data['close'].rolling(window=self.short_window).mean()
        long_mavg = data['close'].rolling(window=self.long_window).mean()

        # 创建信号：当短期均线上穿长期均线时为1，下穿时为-1
        # .iloc[-1] 获取最新值
        if short_mavg.iloc[-1] > long_mavg.iloc[-1] and short_mavg.iloc[-2] < long_mavg.iloc[-2]:
            return [{'date': data['trade_date'].iloc[-1], 'signal': 'buy'}]
        elif short_mavg.iloc[-1] < long_mavg.iloc[-1] and short_mavg.iloc[-2] > long_mavg.iloc[-2]:
            return [{'date': data['trade_date'].iloc[-1], 'signal': 'sell'}]
        
        return []
"""

STRATEGY_TEMPLATES = {
    "ma_crossover": MA_CROSSOVER_TEMPLATE,
    "empty": "# Empty strategy template\n\nfrom app.services.strategy_base import BaseStrategy\n\nclass Strategy(BaseStrategy):\n    def set_parameters():\n        pass\n\n    def initialize():\n        pass\n\n    def handle_data(self, data):\n        return []\n"
}
# --- END OF TEMPLATES ---


# Define the directory for storing strategy files
STRATEGIES_DIR = Path("/strategies_code")
STRATEGIES_DIR.mkdir(exist_ok=True) # Ensure the directory exists

def get_strategy(db: Session, strategy_id: int):
    return db.query(Strategy).options(joinedload(Strategy.backtest_results)).filter(Strategy.id == strategy_id).first()

def get_strategy_by_name(db: Session, name: str):
    return db.query(Strategy).filter(Strategy.name == name).first()

def get_strategies(db: Session, owner: str, skip: int = 0, limit: int = 100):
    return db.query(Strategy).options(joinedload(Strategy.backtest_results)).filter(Strategy.owner == owner).offset(skip).limit(limit).all()

def get_all_strategies(db: Session):
    return db.query(Strategy).all()


def create_strategy(db: Session, strategy: StrategyCreate, owner: str):
    script_filename = f"strategy_{uuid.uuid4()}.py"
    script_path = STRATEGIES_DIR / script_filename

    # Determine content: from template, direct content, or default to empty
    if strategy.template_name and strategy.template_name in STRATEGY_TEMPLATES:
        script_content_to_write = STRATEGY_TEMPLATES[strategy.template_name]
    else:
        script_content_to_write = strategy.content or STRATEGY_TEMPLATES["empty"]
    
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content_to_write)
    except Exception as e:
        print(f"ERROR writing to {script_path}: {e}")

    strategy_data_for_db = {
        "name": strategy.name,
        "description": strategy.description,
        "script_path": str(script_path),
        "owner": owner
    }

    db_strategy = Strategy(**strategy_data_for_db)
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def update_strategy_status(db: Session, strategy_id: int, status: str):
    db_strategy = get_strategy(db, strategy_id)
    if db_strategy:
        db_strategy.status = status
        db.commit()
        db.refresh(db_strategy)
    return db_strategy

def update_strategy(db: Session, strategy_id: int, strategy_in: StrategyUpdate):
    db_strategy = get_strategy(db, strategy_id)
    if not db_strategy:
        return None

    update_data = strategy_in.model_dump(exclude_unset=True)
    
    if "script_content" in update_data:
        script_content = update_data.pop("script_content")
        try:
            # Ensure script_path exists and is valid before writing
            if db_strategy.script_path:
                with open(db_strategy.script_path, "w", encoding="utf-8") as f:
                    f.write(script_content)
        except (FileNotFoundError, TypeError):
            # Handle cases where script_path might be None or invalid
            # Or log an error
            pass

    for key, value in update_data.items():
        setattr(db_strategy, key, value)

    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def delete_strategy(db: Session, strategy_id: int):
    db_strategy = get_strategy(db, strategy_id)
    if not db_strategy:
        return None
    
    try:
        Path(db_strategy.script_path).unlink(missing_ok=True)
    except TypeError:
        pass

    db.delete(db_strategy)
    db.commit()
    return db_strategy