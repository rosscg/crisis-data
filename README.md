App currently takes screen name as input and saves data to DB.


Local installation:
Install Redis from https://redis.io/ or brew, and follow instructions.
Build project.
Run Celery worker: $ celery -A homesite worker -l info
