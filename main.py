import argparse

from src.config_manager import load_config
from src.log_utils import get_log_path, mirrored_output
from src.runner import run_automation


def main():
    parser = argparse.ArgumentParser(description="Job automation launcher")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the automation immediately using config.py instead of opening the UI.",
    )
    args = parser.parse_args()

    if args.run:
        with mirrored_output():
            try:
                print(f"Writing logs to {get_log_path()}")
                run_automation(load_config())
            except Exception as e:
                print(f"\nScript failed with error: {str(e)}")
        return

    from src.ui import launch_ui

    launch_ui()

if __name__ == "__main__":
    main()
