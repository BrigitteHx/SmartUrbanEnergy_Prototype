import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'postgresql://postgres:password@localhost:5432/smart_urban_energy_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False