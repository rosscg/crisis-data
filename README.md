App currently takes screen name as input and saves data to DB.


Local installation:
Install Redis from https://redis.io/ or brew, and follow instructions.
Build project, create virtual environment, and install dependencies.

Run Server: $ python manage.py runserver
  Log in to the admin interface and add a period task to 'update_user_relos_task' daily
Run Celery worker: $ celery -A homesite worker -l info
Run Celery beat: $ celery -A homesite beat -l info -S django
