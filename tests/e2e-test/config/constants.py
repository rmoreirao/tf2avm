import os

from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("URL", "http://localhost:8000")
if URL.endswith("/"):
    URL = URL[:-1]