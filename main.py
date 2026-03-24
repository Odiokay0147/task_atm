import sys
import os

# Fix import issues
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Processing.analyse_data import main as analyse_data_main


def run():
    print("Starting ATM Data Analysis...\n")

    analyse_data_main()

    print("\nAnalysis Completed Successfully!")


if __name__ == "__main__":
    run()