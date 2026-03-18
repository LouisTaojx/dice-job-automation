import argparse

from src.config_manager import load_config
from src.runner import run_automation


def main():
    parser = argparse.ArgumentParser(description="Dice job automation launcher")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the automation immediately using config.py instead of opening the UI.",
    )
    args = parser.parse_args()

    if args.run:
        try:
            run_automation(load_config())
        except Exception as e:
            print(f"\nScript failed with error: {str(e)}")
        return

    from src.ui import launch_ui

    launch_ui()

if __name__ == "__main__":
    main()
