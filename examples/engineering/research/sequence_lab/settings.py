from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    seed: int = 19
    width: int = 8
    train_steps: int = 180
    finetune_steps: int = 80
    learning_rate: float = 0.02
