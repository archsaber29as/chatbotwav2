"""Run this script LOCALLY (not on Railway) to refresh your Google token.
It opens a browser for OAuth, saves token.pickle, and prints the base64
string to paste into Railway as GOOGLE_TOKEN_B64."""

import os, base64, pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks",
]

creds = None
if os.path.exists("token.pickle"):
    with open("token.pickle", "rb") as f:
        creds = pickle.load(f)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        print("✅ Token refreshed successfully.")
    else:
        flow  = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        print("✅ New token obtained successfully.")
    with open("token.pickle", "wb") as f:
        pickle.dump(creds, f)

with open("token.pickle", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

print("\n" + "="*60)
print("Copy this value into Railway → Variables → GOOGLE_TOKEN_B64:")
print("="*60)
print(b64)
print("="*60 + "\n")
