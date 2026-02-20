cd ~/base_template/project
source venv/bin/activate
python manage.py collectstatic --noinput
pkill -HUP gunicorn
cd ~/base_template/project
source venv/bin/activate
# Перевірити чи gunicorn працює
ps aux | grep "gunicorn.*8000" | grep -v grep

# Перезапустити gunicorn з правильним timeout
pkill gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 300 --daemon project.wsgi:application

# Перевірити статус
ps aux | grep gunicorn | grep -v grep
exit()

exit
# Перезапустити gunicorn з timeout
pkill gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 300 --daemon project.wsgi:application

# Перевірити
ps aux | grep gunicorn | grep -v grep

# Перезапустити nginx
systemctl reload nginx
