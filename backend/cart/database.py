from flask_sqlalchemy import SQLAlchemy 
from flask import Flask
import os

db = SQLAlchemy()

def init_db(app: Flask):
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/meubanco')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

    db.init_app(app)

    with app.app_context():
        db.create_all()

