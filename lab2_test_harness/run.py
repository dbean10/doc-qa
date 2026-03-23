# lab2/run.py
# Entry point. Run with: uv run python lab2/run.py

from harness import HarnessRunner, Logger
from variants import VARIANTS
from inputs import INPUTS


def main() -> None:
    print("Week 2 — Prompt Testing Harness")
    print(f"Variants: {len(VARIANTS)}  Inputs: {len(INPUTS)}  "
          f"Total calls: {len(VARIANTS) * len(INPUTS)}")
    print()

    runner = HarnessRunner(variants=VARIANTS, inputs=INPUTS)
    results = runner.run()

    logger = Logger()
    output_path = logger.write(results)
    logger.print_summary(results)

    print(f"\nResults written to: {output_path}")


if __name__ == "__main__":
    main()