# backend/app/crud/crud_strategy.py
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
    script_filename = f"strategy_{uuid.uuid4()}.py"
    script_path = STRATEGIES_DIR / script_filename

    script_content_to_write = strategy.content
    
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content_to_write)
    except Exception as e:
        print(f"ERROR writing to {script_path}: {e}")

    db_strategy = Strategy(
        name=strategy.name,
        description=strategy.description,
        script_path=str(script_path),
        content=script_content_to_write,
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

    update_data = strategy_in.model_dump(exclude_unset=True)
    
    if "script_content" in update_data:
        script_content = update_data.pop("script_content")
        try:
            with open(db_strategy.script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            db_strategy.content = script_content
        except (FileNotFoundError, TypeError):
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