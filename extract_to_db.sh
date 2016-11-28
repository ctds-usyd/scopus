#!/bin/bash -x
PYTHONPATH=`pwd` DJANGO_SETTINGS_MODULE=Scopus.settings python Scopus/db_loader.py $@
