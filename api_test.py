from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"src"))

from competition_ai.config import SETTINGS
from competition_ai.llm import ThaiLLMClient

def main():
    client = ThaiLLMClient(SETTINGS)
    print(client.generate(
        "ตอบสั้นมาก ห้ามมี <think>",
        "ตอบคำว่า API_OK เพียงคำเดียว"
    ))

if __name__ == "__main__":
    main()
