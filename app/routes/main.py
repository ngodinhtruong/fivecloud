from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.like import Like
from app.models.post import Post
from app.models.user import User
from app.models.comment import Comment
from app.models.saved_post import SavedPost
from werkzeug.utils import secure_filename
import os
# from app.models.notification import Notification
from app import db
from datetime import datetime
from app.services.notification_service import NotificationService
from app.services.ai_assistant import AIAssistant, AIAssistantError
from app.models.follow import Follow
from flask_socketio import emit
from app import socketio
from app.sockets import notification
import logging

logger = logging.getLogger(__name__)
from app.services.notification_service import NotificationService
from app.models.notification import Notification
from app.utils.time_vn import vn_now
from app.firebase_service import firebase_bucket

bp = Blueprint('main', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    query = Post.query.order_by(Post.created_at.desc())
    likes = []
    if current_user.is_authenticated and not current_user.is_initial_admin:
        query = query.filter(
            db.or_(
                Post.visibility == 0,
                db.and_(Post.visibility == 1, Post.user_id == current_user.id)
            )
        )
        likes = Like.query.filter_by(user_id=current_user.id).all()
    elif not current_user.is_authenticated:
        query = query.filter(Post.visibility == 0)
    posts = query.paginate(page=page, per_page=10, error_out=False)
    liked_post_ids = [like.post_id for like in likes] if likes else []
    total_likes_query = db.session.query(Like.post_id, db.func.count(Like.post_id).label('like_count'))\
        .group_by(Like.post_id).all()
    total_likes_dict = {post_id: like_count for post_id, like_count in total_likes_query}
    for post in posts.items:
        post.total_likes = total_likes_dict.get(post.id, 0)
    return render_template('main/index.html', posts=posts, likes=liked_post_ids)
def upload_to_firebase(file, filename):
    try:
        blob = firebase_bucket.blob(f"posts/{filename}")
        file.stream.seek(0)
        blob.upload_from_file(file.stream, content_type=file.content_type)
        blob.make_public()
        current_app.logger.error(f"Thanh cong")
        return blob.public_url
    except Exception as e:
        current_app.logger.error(f"Firebase Upload Error: {str(e)}")
        return None
@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if current_user.is_admin():
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_xhr:
            return jsonify({'success': False, 'error': 'Admin không được phép đăng bài.'})
        flash('Admin không được phép đăng bài.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        source_link = request.form.get('source_link')
        source_content = request.form.get('source_content')
        tags = request.form.get('tags')
        visibility = request.form.get('visibility')
        
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if not title or not content:
            if is_xhr:
                return jsonify({'success': False, 'error': 'Tiêu đề và nội dung không được để trống.'})
            flash('Tiêu đề và nội dung không được để trống.', 'error')
            return redirect(url_for('main.create_post'))

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if not allowed_file(file.filename):
                    if is_xhr:
                        return jsonify({'success': False, 'error': 'Định dạng file không được hỗ trợ.'})
                    flash('Định dạng file không được hỗ trợ.', 'error')
                    return redirect(url_for('main.create_post'))
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                max_size = 10 * 1024 * 1024
                if file_size > max_size:
                    if is_xhr:
                        return jsonify({'success': False, 'error': 'Ảnh quá lớn. Kích thước tối đa là 10MB.'})
                    flash('Ảnh quá lớn. Kích thước tối đa là 10MB.', 'error')
                    return redirect(url_for('main.create_post'))

                ext = file.filename.rsplit('.', 1)[1].lower()
                timestamp = vn_now().strftime('%Y%m%d_%H%M%S')
                filename = secure_filename(f"{current_user.username}_{timestamp}.{ext}")
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'posts')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                upload_to_firebase(file, filename)
                image_url = f"/static/uploads/posts/{filename}"

        post = Post(
            title=title,
            content=content,
            source_link=source_link,
            source_content=source_content,
            tags=tags,
            user_id=current_user.id,
            status='approved',
            visibility=visibility,
            image_url=filename
        )

        try:
            db.session.add(post)
            db.session.commit()
            if is_xhr:
                return jsonify({
                    'success': True,
                    'message': 'Bài viết đã được đăng thành công.',
                    'redirect_url': url_for('main.view_post', post_id=post.id)
                })
            flash('Bài viết đã được đăng thành công.', 'success')
            followers = Follow.query.filter_by(followed_id=current_user.id).all()
            message = f'{current_user.full_name} vừa đăng bài mới!'


            for follower in followers:
                # Tạo thông báo trong database
                notification = NotificationService.create_post_notification(
                    user_id=follower.follower_id,
                    message=message,
                    post_id=post.id,
                    type = 'create-post'
                )
                
                if notification:
                    # Gửi thông báo realtime qua socket
                    socketio.emit('action_post', {
                        'message': message,
                        'user_id': follower.follower_id,
                        'post_id': post.id,
                        'type' : 'create-post'
                    }, room=f'user_{follower.follower_id}')
                    print('Thanh cong')
                else:
                    print('khong')
            return redirect(url_for('main.view_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            if is_xhr:
                return jsonify({'success': False, 'error': 'Có lỗi xảy ra khi tạo bài viết.'})
            flash('Có lỗi xảy ra khi tạo bài viết.', 'error')
    
    visibility = request.args.get('visibility', 0)
    return render_template('main/create_post.html', visibility=visibility)

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
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.desc()).all()
    likes = []
    if current_user.is_authenticated:
        likes = [like.post_id for like in Like.query.filter_by(user_id=current_user.id).all()]
    return render_template('main/view_post.html', post=post, comments=comments, likes=likes)


@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_xhr:
            return jsonify({'success': False, 'error': 'Bạn không có quyền chỉnh sửa bài viết này.'+ str(e)})
        flash('Bạn không có quyền chỉnh sửa bài viết này.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        title = request.form.get('title')
        content = request.form.get('content')
        source_link = request.form.get('source_link')
        source_content = request.form.get('source_content')
        tags = request.form.get('tags')
        visibility = request.form.get('visibility')
        
        if not title or not content:
            if is_xhr:
                return jsonify({'success': False, 'error': 'Tiêu đề và nội dung không được để trống.'})
            flash('Tiêu đề và nội dung không được để trống.', 'error')
            return redirect(url_for('main.edit_post', post_id=post_id))

        post.title = title
        post.content = content
        post.source_link = source_link
        post.source_content = source_content
        post.tags = tags
        post.visibility = visibility
        post.updated_at = vn_now()

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if not allowed_file(file.filename):
                    if is_xhr:
                        return jsonify({'success': False, 'error': 'Định dạng file không được hỗ trợ.'})
                    flash('Định dạng file không được hỗ trợ.', 'error')
                    return redirect(url_for('main.edit_post', post_id=post_id))
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                max_size = 10 * 1024 * 1024
                if file_size > max_size:
                    if is_xhr:
                        return jsonify({'success': False, 'error': 'Ảnh quá lớn. Kích thước tối đa là 10MB.'})
                    flash('Ảnh quá lớn. Kích thước tối đa là 10MB.', 'error')
                    return redirect(url_for('main.edit_post', post_id=post_id))

                # Xóa ảnh cũ
                if post.image_url:
                    old_image_path = os.path.join(current_app.root_path, 'static', 'uploads', 'posts', post.image_url.split('/')[-1])
                    current_app.logger.info(f"Attempting to delete old image: {old_image_path}")
                    if os.path.isfile(old_image_path):
                        try:
                            # Kiểm tra quyền trước khi xóa
                            if not os.access(old_image_path, os.W_OK):
                                current_app.logger.error(f"No write permission for {old_image_path}")
                                if is_xhr:
                                    return jsonify({'success': False, 'error': 'Không có quyền xóa ảnh cũ.'})
                                flash('Không có quyền xóa ảnh cũ.', 'error')
                                return redirect(url_for('main.edit_post', post_id=post_id))
                            os.remove(old_image_path)
                            current_app.logger.info(f"Successfully deleted old image: {old_image_path}")
                        except OSError as e:
                            current_app.logger.error(f"Failed to delete old image {old_image_path}: {str(e)}")
                            if is_xhr:
                                return jsonify({'success': False, 'error': f'Không thể xóa ảnh cũ: {str(e)}'})
                            flash(f'Không thể xóa ảnh cũ: {str(e)}', 'error')
                            return redirect(url_for('main.edit_post', post_id=post_id))
                    else:
                        current_app.logger.warning(f"Old image not found: {old_image_path}")

                # Lưu ảnh mới
                ext = file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.uctnow()
                filename = secure_filename(f"{current_user.username}_{timestamp}.{ext}")
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'posts')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                try:
                    # Kiểm tra quyền ghi thư mục
                    if not os.access(upload_folder, os.W_OK):
                        current_app.logger.error(f"No write permission for {upload_folder}")
                        if is_xhr:
                            return jsonify({'success': False, 'error': 'Không có quyền ghi vào thư mục upload.'})
                        flash('Không có quyền ghi vào thư mục upload.', 'error')
                        return redirect(url_for('main.edit_post', post_id=post_id))
                    file.save(file_path)
                    post.image_url = f"/static/uploads/posts/{filename}"
                    current_app.logger.info(f"New image saved: {file_path}, image_url set to {post.image_url}")
                except Exception as e:
                    current_app.logger.error(f"Failed to save new image {file_path}: {str(e)}")
                    if is_xhr:
                        return jsonify({'success': False, 'error': f'Không thể lưu ảnh: {str(e)}'})
                    flash(f'Không thể lưu ảnh: {str(e)}', 'error')
                    return redirect(url_for('main.edit_post', post_id=post_id))
        
        try:
            db.session.commit()
            if is_xhr:
                return jsonify({
                    'success': True,
                    'message': 'Bài viết đã được cập nhật thành công.',
                    'redirect_url': url_for('main.view_post', post_id=post.id)
                })
            flash('Bài viết đã được cập nhật thành công.', 'success')
            return redirect(url_for('main.view_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to commit changes: {str(e)}")
            if is_xhr:
                return jsonify({'success': False, 'error': 'Có lỗi xảy ra khi cập nhật bài viết.'+ str(e)})
            flash('Có lỗi xảy ra khi cập nhật bài viết.' + e, 'error')
            return redirect(url_for('main.edit_post', post_id=post_id))
            
    return render_template('main/edit_post.html', post=post)
@bp.route('/mention-users')
@login_required
def mention_users():
    q = request.args.get('q', '').strip().lower()
    followed_users = User.query.join(Follow, Follow.followed_id == User.id) \
        .filter(Follow.follower_id == current_user.id) \
        .filter(User.username.ilike(f'%{q}%')) \
        .all()

    return jsonify([{
        'username': u.username,
        'full_name': u.full_name or '',
        'avatar_url': u.avatar_url or User.generate_random_avatar()
    } for u in followed_users])


@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if post.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bài viết này.'}), 403

    try:
        # Delete all saved_posts records associated with this post
        SavedPost.query.filter_by(post_id=post_id).delete()
        
        # Delete associated image if it exists
        if post.image_url:
            image_path = os.path.join(current_app.root_path, 'static', 'uploads', 'posts', post.image_url.split('/')[-1])
            if os.path.isfile(image_path):
                try:
                    if not os.access(image_path, os.W_OK):
                        current_app.logger.error(f"No write permission for {image_path}")
                        return jsonify({'success': False, 'message': 'Không có quyền xóa ảnh của bài viết.'}), 500
                    os.remove(image_path)
                    current_app.logger.info(f"Successfully deleted image for post {post_id}: {image_path}")
                except OSError as e:
                    current_app.logger.error(f"Failed to delete image {image_path}: {str(e)}")
                    return jsonify({'success': False, 'message': f'Không thể xóa ảnh của bài viết: {str(e)}'}), 500
            else:
                current_app.logger.warning(f"Image not found for post {post_id}: {image_path}")
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Bài viết đã được xóa.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete post {post_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra khi xóa bài viết.'}), 500


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

@bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    user_id_post = post.user_id

    if not current_user.is_authenticated:
        flash('Bạn cần đăng nhập để bình luận.', 'warning')
    if request.method == 'POST':  
        content = request.form.get('comment')
        if not content:
            flash('Nội dung bình luận không được để trống.', 'warning')
            return redirect(url_for('main.view_post', post_id=post_id))
        
        comment = Comment(
            content=content,
            user_id=current_user.id,
            post_id=post.id
        )
        try:
            db.session.add(comment)
            db.session.commit()
            if current_user.id != user_id_post:
                message = f'{current_user.full_name} đã bình luận vào bài viết của bạn'
                
                notification = NotificationService.create_post_notification(
                    user_id=user_id_post,
                    message=message,
                    post_id=post.id,
                    type='comment-post'
                )

                if notification:
                    socketio.emit('action_post', {
                        'user_id': user_id_post,
                        'message': message,
                        'post_id': post.id,
                        'type': 'comment-post'
                    }, room=f"user_{user_id_post}")
            flash('Bình luận của bạn đã được đăng.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi đăng bình luận.', 'error')
    
    return redirect(url_for('main.view_post', post_id=post_id))

@bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    post = Post.query.get_or_404(post_id)
    user_id_post = post.user_id
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    try:
        if existing_like:
            db.session.delete(existing_like)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Đã bỏ thích bài viết',
                'status': 'unliked'
            })

        # Thêm like mới
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)
        db.session.commit()

        # Không cần gửi thông báo cho chính mình
        if current_user.id != user_id_post:
            message = f'{current_user.full_name} đã thích bài viết của bạn'
            
            notification = NotificationService.create_post_notification(
                user_id=user_id_post,
                message=message,
                post_id=post.id,
                type='like-post'
            )

            if notification:
                socketio.emit('action_post', {
                    'user_id': user_id_post,
                    'message': message,
                    'post_id': post.id,
                    'type': 'like-post'
                }, room=f"user_{user_id_post}")
                
        return jsonify({
            'success': True,
            'message': 'Đã thích bài viết',
            'status': 'liked'
        })

    except Exception as e:
        db.session.rollback()
        flash('Có lỗi xảy ra khi xử lý like.', 'error')
        return jsonify({'success': False, 'message': 'Lỗi hệ thống'}), 500


@bp.route('/api/ai/suggestions', methods=['POST'])
@login_required
def get_ai_suggestions():
    """Get AI suggestions for writing tasks"""
    try:
        data = request.get_json()
        content = data.get('content')
        task_type = data.get('task_type')
        
        if not content or not task_type:
            return jsonify({'error': 'Missing content or task type'}), 400
            
        ai = AIAssistant()
        suggestions = ai.get_writing_suggestions(content, task_type)
        return jsonify(suggestions)
        
    except AIAssistantError as e:
        current_app.logger.error(f"AI Assistant error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/api/ai/chat', methods=['POST'])
@login_required
def chat_with_ai():
    """Chat with AI assistant"""
    try:
        data = request.get_json()
        message = data.get('message')
        context = data.get('context')
        
        if not message:
            return jsonify({'error': 'Missing message'}), 400
            
        ai = AIAssistant()
        response = ai.get_chat_response(message, context)
        return jsonify({'response': response})
        
    except AIAssistantError as e:
        current_app.logger.error(f"AI Assistant error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    if current_user.id == user_id:
        return jsonify({
            'success': False,
            'message': 'Bạn không thể follow chính mình'
        })

    user_to_follow = User.query.get_or_404(user_id)
    existing_follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()

    if existing_follow:
        return jsonify({
            'success': False,
            'message': 'Bạn đã follow người dùng này'
        })

    follow = Follow(follower_id=current_user.id, followed_id=user_id)
    db.session.add(follow)
    db.session.commit()

    message = f'{current_user.full_name} đã theo dõi bạn'
    
    # Gửi notification
    notification = NotificationService.create_post_notification(
        user_id=user_id,
        message=message,
        post_id=current_user.id,
        type='follow-post'
    )

    if notification:
        socketio.emit('follow_action', {
            'user_id': user_id,
            'message': message,
            'follower': current_user.username,
            'type': 'follow-post'
        }, room=f'user_{user_id}')
    return jsonify({
        'success': True,
        'message': f'Đã follow {user_to_follow.username}'
    })

@bp.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first_or_404()
    
    db.session.delete(follow)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Đã unfollow thành công'
    })

@bp.route('/follow')
@login_required
def follow():
    """Hiển thị trang Follow với hai tab: Người theo dõi và Đang theo dõi"""
    active_tab = request.args.get('tab', 'followers')
    
    followers = Follow.query.filter_by(followed_id=current_user.id).all()
    following = Follow.query.filter_by(follower_id=current_user.id).all()
    
    return render_template('main/follow.html',
                         followers=followers,
                         following=following,
                         active_tab=active_tab)

@bp.route('/followers')
@login_required
def followers():
    """Chuyển hướng đến trang Follow với tab Người theo dõi"""
    return redirect(url_for('main.follow', tab='followers'))

@bp.route('/following')
@login_required
def following():
    """Chuyển hướng đến trang Follow với tab Đang theo dõi"""
    return redirect(url_for('main.follow', tab='following'))

# Thong bao
@bp.route('/notifications')
@login_required
def notifications():
    notifications = NotificationService.get_user_notifications(current_user.id, limit=100)
    return render_template('main/notifications.html', notifications=notifications)

@bp.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền thực hiện thao tác này'})
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Đã đánh dấu thông báo đã đọc'})
