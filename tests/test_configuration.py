from pathlib import Path

def test_no_real_secrets_in_examples():
    for name in [".env.example","services/scheduling-service/.env.example","services/attendance-service/.env.example","services/ai-vision-service/.env.example"]:
        text=Path(name).read_text()
        assert "postgresql://USER:PASSWORD@HOST" in text
        assert "replace-with" in text
