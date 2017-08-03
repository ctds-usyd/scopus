set PYTHONPATH=%CD%
set DJANGO_SETTINGS_MODULE=Scopus.settings
python Scopus/db_loader.py %*
