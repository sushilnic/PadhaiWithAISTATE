#!/bin/bash
set -e
cd school_project
export PYTHONPATH=/code/school_project
gunicorn school_project.wsgi:application --log-file - --bind 0.0.0.0:8000
