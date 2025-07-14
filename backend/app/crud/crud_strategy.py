from sqlalchemy.orm import Session, joinedload
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate
import uuid
from pathlib import Path

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
    # Generate a unique filename for the script
    script_filename = f"strategy_{uuid.uuid4()}.py"
    script_path = STRATEGIES_DIR / script_filename

    # Define a default script template
    default_script = """# 这是一个简单的双均线策略示例
# 当短期均线（如5日线）上穿长期均线（如20日线）时，做多
# 当短期均线下穿长期均线时，平仓

def initialize(context):
    # 设置策略参数
    context.short_ma = 5
    context.long_ma = 20
    context.symbol = 'SHFE.rb2501' # 订阅的合约
    context.amount = 1 # 每次下单手数

    # 订阅行情
    context.subscribe(context.symbol)

def handle_data(context, data):
    # 获取历史数据
    hist = context.history(context.symbol, 'close', context.long_ma + 1, '1d')
    if hist is None or len(hist) < context.long_ma:
        return

    # 计算均线
    short_ma = hist[-context.short_ma:].mean()
    long_ma = hist[-context.long_ma:].mean()

    # 获取当前持仓
    position = context.get_position(context.symbol)

    # 金叉���短期均线上穿长期均线
    if short_ma > long_ma and position is None:
        print(f"金叉形成，在价格 {data.close} 买入")
        context.buy(context.symbol, context.amount)

    # 死叉：短期均线下穿长期均线
    elif short_ma < long_ma and position is not None:
        print(f"死叉形成，在价格 {data.close} 平仓")
        context.sell(context.symbol, position.volume)
"""

    # Use provided script content or the default template
    script_content_to_write = strategy.script_content if strategy.script_content else default_script

    # Write the script content to the file
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content_to_write)
        
        # --- DEBUGGING ---
        print(f"--- CRUD DEBUG (CREATE) ---")
        print(f"Attempted to write to: {script_path}")
        print(f"File exists after write: {script_path.exists()}")
        print(f"--------------------------")
        # --- END DEBUGGING ---

    except Exception as e:
        # --- DEBUGGING ---
        print(f"--- CRUD DEBUG (CREATE) ---")
        print(f"ERROR writing to {script_path}: {e}")
        print(f"--------------------------")
        # --- END DEBUGGING ---


    # Create the database model instance
    db_strategy = Strategy(
        name=strategy.name,
        description=strategy.description,
        script_path=str(script_path), # Store the path as a string
        owner=owner
    )
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

    # Update model fields
    update_data = strategy_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "script_content":
            continue # We handle script content separately
        setattr(db_strategy, key, value)

    # If new script content is provided, overwrite the file
    if strategy_in.script_content:
        try:
            with open(db_strategy.script_path, "w") as f:
                f.write(strategy_in.script_content)
        except (FileNotFoundError, TypeError):
            # Handle case where script_path is somehow invalid
            # For simplicity, we'll just ignore this error, but in production you might log it
            pass

    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def delete_strategy(db: Session, strategy_id: int):
    db_strategy = get_strategy(db, strategy_id)
    if not db_strategy:
        return None
    
    # Delete the script file
    try:
        Path(db_strategy.script_path).unlink(missing_ok=True)
    except TypeError:
        # script_path might be None or invalid
        pass

    db.delete(db_strategy)
    db.commit()
    return db_strategy

