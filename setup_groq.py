"""Run locally in an interactive terminal; never paste credentials into chat."""
import getpass
import json
from pathlib import Path


def main():
    destination = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if destination.exists():
        print("Configuration already exists. Edit .streamlit/secrets.toml locally to preserve your settings.")
        return
    print("Groq setup for the free-plan experiment (no billing changes).")
    print("Create a key at https://console.groq.com/keys then paste it below.")
    print("Input is hidden. The key is saved locally in the Git-ignored Streamlit secrets file.")
    key = getpass.getpass("Groq API key: ").strip()
    if not key:
        print("No key entered. Nothing was saved.")
        return
    values = {
        "LLM_PROVIDER": "compatible_api",
        "LLM_BASE_URL": "https://api.groq.com/openai/v1",
        "LLM_MODEL": "openai/gpt-oss-20b",
        "LLM_API_KEY": key,
    }
    destination.parent.mkdir(exist_ok=True)
    with destination.open("x", encoding="utf-8") as file:
        file.write("# Local credentials. Never commit or share this file.\n")
        for name, value in values.items():
            file.write(f"{name} = {json.dumps(value)}\n")
    print("Settings saved. Connection has NOT yet been tested.")
    print("Restart Streamlit, select Connected model, and analyze a synthetic job first.")


if __name__ == "__main__":
    main()
