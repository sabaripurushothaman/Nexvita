from datetime import datetime
from database.db import db


class AIHistory(db.Model):
    __tablename__ = 'ai_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    conversation_id = db.Column(db.String(100))
    message_type = db.Column(db.String(20))  # user, ai, system
    content = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Numeric(3, 2))   # -1.00 to 1.00
    urgency_level = db.Column(db.Integer, default=0) # 0=low, 1=medium, 2=high, 3=emergency
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # NOTE: The 'ai_history' back-reference is already declared
    # in user.py via User.ai_history relationship backref.
    # Adding it here again would cause an SQLAlchemy mapper conflict.

    def __repr__(self):
        return f'<AIHistory {self.id} - {self.message_type}>'