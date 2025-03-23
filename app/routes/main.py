from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.post import Post
from app.models.user import User
from app import db
from datetime import datetime
from app.models.saved_post import SavedPost

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Trang chủ - hiển thị tất cả bài viết"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('main/index.html', posts=posts)

@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    """Tạo bài viết mới"""
    if current_user.is_admin():
        flash('Admin không được phép đăng bài.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        source_link = request.form.get('source_link')
        source_content = request.form.get('source_content')
        tags = request.form.get('tags')

        if not title or not content:
            flash('Tiêu đề và nội dung không được để trống.', 'error')
            return redirect(url_for('main.create_post'))

        post = Post(
            title=title,
            content=content,
            source_link=source_link,
            source_content=source_content,
            tags=tags,
            user_id=current_user.id,
            status='approved'  # Bài viết được đăng trực tiếp
        )

        try:
            db.session.add(post)
            db.session.commit()
            flash('Bài viết đã được đăng thành công.', 'success')
            return redirect(url_for('main.view_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi tạo bài viết.', 'error')

    return render_template('main/create_post.html')

@bp.route('/my-posts')
@login_required
def my_posts():
    """Xem danh sách bài viết của mình"""
    if current_user.is_admin():
        flash('Admin không có bài viết cá nhân.', 'error')
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id=current_user.id)\
        .order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('main/my_posts.html', posts=posts)

@bp.route('/post/<int:post_id>')
def view_post(post_id):
    """Xem chi tiết bài viết"""
    post = Post.query.get_or_404(post_id)
    return render_template('main/view_post.html', post=post)

@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Chỉnh sửa bài viết"""
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        flash('Bạn không có quyền chỉnh sửa bài viết này.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.source_link = request.form.get('source_link')
        post.source_content = request.form.get('source_content')
        post.tags = request.form.get('tags')
        post.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Bài viết đã được cập nhật thành công.', 'success')
            return redirect(url_for('main.view_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi cập nhật bài viết.', 'error')
            
    return render_template('main/edit_post.html', post=post)

@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """Xóa bài viết"""
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        flash('Bạn không có quyền xóa bài viết này.', 'error')
        return redirect(url_for('main.index'))

    try:
        db.session.delete(post)
        db.session.commit()
        flash('Bài viết đã được xóa.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Có lỗi xảy ra khi xóa bài viết.', 'error')
        
    return redirect(url_for('main.my_posts'))

@bp.route('/post/<int:post_id>/toggle_save', methods=['POST'])
@login_required
def toggle_save_post(post_id):
    post = Post.query.get_or_404(post_id)
    saved_post = SavedPost.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if saved_post:
        db.session.delete(saved_post)
        message = 'Đã bỏ lưu bài viết'
        status = 'unsaved'
    else:
        saved_post = SavedPost(user_id=current_user.id, post_id=post_id)
        db.session.add(saved_post)
        message = 'Đã lưu bài viết'
        status = 'saved'
    
    db.session.commit()
    return jsonify({
        'success': True,
        'message': message,
        'status': status
    })

@bp.route('/saved-posts')
@login_required
def saved_posts():
    saved = SavedPost.query.filter_by(user_id=current_user.id)\
        .order_by(SavedPost.saved_at.desc())\
        .all()
    return render_template('main/saved_posts.html', saved_posts=saved) 