web: gunicorn school_project.wsgi:application --chdir /code/school_project --bind 0.0.0.0:8080
release: cd school_project && python manage.py migrate
