from dotenv import load_dotenv
import os
load_dotenv()

token = os.getenv('FINMIND_TOKEN', '')
print("Token from .env:", repr(token))
