from sequence_lab.pipeline import run_pipeline

if __name__ == "__main__":
    report = run_pipeline(".")
    print({key:report[key] for key in ("validation_mse", "validation_samples", "optimized")})
