from enum import unique
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def setup_db(app):
    db.app = app
    db.init_app(app)
    db.create_all()  # creates the sqlite file if it doesn't exist


class scan_results(db.Model):

    __tablename__ = 'scan_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=False, nullable=False)

    hard_skills = db.Column(db.String, unique=False, nullable=False)
    soft_skills = db.Column(db.String, unique=False, nullable=False)
    best_practices = db.Column(db.String, unique=False, nullable=False)

    sales_index = db.Column(db.String, unique=False, nullable=False)
    similarity_check = db.Column(db.String, unique=False, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()
        # db.session.close()
        return self

    def update(self):
        db.session.commit()
        db.session.close()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        db.session.close()
