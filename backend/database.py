from flask_sqlalchemy import SQLAlchemy 
from flask import Flask

db = SQLAlchemy()

def init_db(app: Flask):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
    db.init_app(app)
    with app.app_context():
        db.create_all()




# import sqlite3



# def get_db_connection():
#     conn = sqlite3.connect('store.db')
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     conn = get_db_connection()
#     with open('schema.sql') as f:
#         conn.executescript(f.read())
#     conn.close()


