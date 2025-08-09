from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from database import Database
import secrets
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

# Инициализация базы данных
db = Database()

# Проверка авторизации
def require_auth():
    if 'user_id' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    return None

# API маршруты

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'error': 'Все поля обязательны'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Пароль должен содержать минимум 6 символов'}), 400
        
        user_id = db.create_user(username, email, password)
        
        # Создание сессии
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'message': 'Регистрация успешна',
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'avatar': username[0].upper()
            }
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        login_field = data.get('login', '').strip()
        password = data.get('password', '')
        
        if not login_field or not password:
            return jsonify({'error': 'Логин и пароль обязательны'}), 400
        
        user = db.authenticate_user(login_field, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            return jsonify({
                'message': 'Вход выполнен успешно',
                'user': user
            })
        else:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
            
    except Exception as e:
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Выход выполнен успешно'})

@app.route('/api/user', methods=['GET'])
def get_current_user():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    user = db.get_user(session['user_id'])
    if user:
        return jsonify({'user': user})
    else:
        return jsonify({'error': 'Пользователь не найден'}), 404

@app.route('/api/posts', methods=['GET'])
def get_posts():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        posts = db.get_posts(limit=limit, offset=offset)
        
        # Добавляем информацию о лайках текущего пользователя
        for post in posts:
            post['is_liked'] = db.is_liked(post['id'], session['user_id'])
        
        return jsonify({'posts': posts})
        
    except Exception as e:
        return jsonify({'error': 'Ошибка получения постов'}), 500

@app.route('/api/posts', methods=['POST'])
def create_post():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        image_url = data.get('image_url', '')
        
        if not content:
            return jsonify({'error': 'Содержимое поста не может быть пустым'}), 400
        
        post_id = db.create_post(session['user_id'], content, image_url)
        
        return jsonify({
            'message': 'Пост создан успешно',
            'post_id': post_id
        })
        
    except Exception as e:
        return jsonify({'error': 'Ошибка создания поста'}), 500

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = session['user_id']
        
        if db.is_liked(post_id, user_id):
            db.remove_like(post_id, user_id)
            action = 'removed'
        else:
            db.add_like(post_id, user_id)
            action = 'added'
        
        return jsonify({
            'message': f'Лайк {action}',
            'action': action
        })
        
    except Exception as e:
        return jsonify({'error': 'Ошибка при обработке лайка'}), 500

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        comments = db.get_comments(post_id)
        return jsonify({'comments': comments})
        
    except Exception as e:
        return jsonify({'error': 'Ошибка получения комментариев'}), 500

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Комментарий не может быть пустым'}), 400
        
        comment_id = db.add_comment(post_id, session['user_id'], content)
        
        return jsonify({
            'message': 'Комментарий добавлен',
            'comment_id': comment_id
        })
        
    except Exception as e:
        return jsonify({'error': 'Ошибка добавления комментария'}), 500

# Статические файлы
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

if __name__ == '__main__':
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    print("Сервер Aura запускается...")
    print("Доступно по адресу: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)