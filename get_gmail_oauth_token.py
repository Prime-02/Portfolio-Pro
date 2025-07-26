from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

# SCOPES for Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES
)
creds = flow.run_local_server(port=8000)

# Save credentials
with open('token.pkl', 'wb') as token:
    pickle.dump(creds, token)

print("Access Token:", creds.token)
print("Refresh Token:", creds.refresh_token)



# Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*uvicorn*" } | Stop-Process -Force