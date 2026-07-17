wsl -d Debian

sudo apt update
sudo apt install postgresql python3 python3-pip python3-venv git -y

pip install psycopg2-binary
pip install https://github.com/aiogram/aiogram/archive/refs/heads/dev-3.x.zip


python3 -m venv /accep/env


sudo -i -u postgres
psql
ALTER USER postgres PASSWORD 'pass';