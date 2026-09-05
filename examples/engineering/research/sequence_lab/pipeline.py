from pathlib import Path
from .settings import Settings
from .data.prepare import prepare
from .training.train import train
from .training.finetune import finetune
from .evaluation.evaluate import evaluate
from shared_math.report import write_report

def run_pipeline(root):
    root = Path(root)
    settings = Settings()
    products = root / "products"
    products.mkdir(exist_ok=True)
    prepared = products / "prepared.npz"
    checkpoint = products / "trained.npz"
    adapted = products / "adapted.npz"
    splits = prepare(root / "data/sequences.csv", prepared)
    train_curve = train(prepared, checkpoint, settings)
    tune_curve = finetune(prepared, checkpoint, adapted, settings)
    observations = evaluate(prepared, adapted, products / "predictions.csv")
    report = dict(observations, splits=splits, training_loss=train_curve, finetuning_loss=tune_curve,
                  encoder="frozen one-block self-attention encoder", optimized="linear regression head only", seed=settings.seed)
    if not train_curve[-1] < train_curve[0] or not tune_curve[-1] < tune_curve[0]:
        raise RuntimeError("Expected training progress was not observed")
    write_report(products / "metrics.json", report)
    return report
