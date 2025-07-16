# backend/app/services/strategy_base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseStrategy(ABC):
    """
    所有策略都应继承的基类。
    它定义了策略与交易环境交互的标准接口。
    """
    def __init__(self, context: Any, **params):
        self.context = context
        self.parameters = {}
        self.set_parameters() # 调用用户定义的参数
        # 如果外部传入了参数（在优化时），则覆盖默认值
        for key, value in params.items():
            if key in self.parameters:
                setattr(self, key, value)

    @abstractmethod
    def initialize(self):
        """
        策略初始化，在策略开始运行时调用一次。
        用于设置参数、订阅行情等。
        """
        pass

    def set_parameters(self):
        """
        用户在此方法中定义策略的可调参数及其默认值。
        """
        pass

    @abstractmethod
    def handle_data(self, data: Dict):
        """
        行情数据处理函数，每个新的行情 bar 或 tick 到来时调用。
        这是策略逻辑的核心。
        """
        pass

    def before_trading_start(self, data: Dict):
        """（可选）在交易日开始前调用。"""
        pass

    def after_trading_end(self, data: Dict):
        """（可选）在交易日结束后调用。"""
        pass