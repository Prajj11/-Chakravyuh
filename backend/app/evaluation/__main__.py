import argparse
from pathlib import Path

from app.evaluation.harness import run

parser = argparse.ArgumentParser(
    description="Freeze calibration and run a disjoint held-out synthetic evaluation once"
)
parser.add_argument("--output", type=Path, default=Path("evaluation/results/heldout-v1.json"))
if __name__ == "__main__":
    run(parser.parse_args().output)
