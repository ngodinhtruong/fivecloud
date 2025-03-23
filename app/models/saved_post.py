from app import db
from datetime import datetime

class SavedPost(db.Model):
    __tablename__ = 'saved_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('saved_posts', lazy=True))
    post = db.relationship('Post', backref=db.backref('saved_by', lazy=True)) 