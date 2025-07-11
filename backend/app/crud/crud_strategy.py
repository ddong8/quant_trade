from sqlalchemy.orm import Session, joinedload
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate
import uuid
from pathlib import Path

# Define the directory for storing strategy files
STRATEGIES_DIR = Path(__file__).parent.parent.parent / "strategies_code"
STRATEGIES_DIR.mkdir(exist_ok=True) # Ensure the directory exists

def get_strategy(db: Session, strategy_id: int):
    return db.query(Strategy).options(joinedload(Strategy.backtest_results)).filter(Strategy.id == strategy_id).first()

def get_strategies(db: Session, owner: str, skip: int = 0, limit: int = 100):
    return db.query(Strategy).options(joinedload(Strategy.backtest_results)).filter(Strategy.owner == owner).offset(skip).limit(limit).all()

def create_strategy(db: Session, strategy: StrategyCreate, owner: str):
    # Generate a unique filename for the script
    script_filename = f"strategy_{uuid.uuid4()}.py"
    script_path = STRATEGIES_DIR / script_filename

    # Write the script content to the file
    with open(script_path, "w") as f:
        f.write(strategy.script_content)

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

