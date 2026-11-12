"""Create local-only secrets, never print them and never replace existing files."""
import base64
import os
from pathlib import Path
import secrets

path = Path(__file__).with_name('.env')
admin, app = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
values = {
    'POSTGRES_PASSWORD': admin, 'APP_DB_PASSWORD': app,
    'TOTP_KEY': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    'AUTH_KEY': secrets.token_urlsafe(48),
    'DEV_ADMIN_DATABASE_URL': f'postgresql+psycopg://familydent:{admin}@127.0.0.1:55432/familydent_dev',
    'DEV_DATABASE_URL': f'postgresql+psycopg://familydent_app:{app}@127.0.0.1:55432/familydent_dev',
    'TEST_ADMIN_DATABASE_URL': f'postgresql+psycopg://familydent:{admin}@127.0.0.1:55433/familydent_test',
    'TEST_DATABASE_URL': f'postgresql+psycopg://familydent_app:{app}@127.0.0.1:55433/familydent_test',
}
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(''.join(f'{key}={value}\n' for key, value in values.items()))
print('Created infra/local/.env (0600); secrets were not printed.')
