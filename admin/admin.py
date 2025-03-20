import time,re,zipfile,os,shutil,hmac,hashlib
from flask import Blueprint, render_template, url_for, redirect, session, request, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from db import db, Posts, Users, Games, MainMenu, Comments
from datetime import datetime,timedelta
from sqlalchemy import func, asc, desc
from werkzeug.utils import secure_filename
from git import Repo

hash = '/test'

admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

menu = [{'url' : '.index', 'title' : 'Панель'},
        {'url' : '.logout', 'title' : 'Выйти'},
        {'url' : '.listusers', 'title' : 'Список пользователей'},
        {'url' : '.listmenu', 'title' : 'Список пунктов меню'},
        {'url' : '.listgames', 'title' : 'Список игр'}]

SECRET_KEY = "6LcPresqAAAAAAz89KkedGqJEDNee9IAcwd5Q0d8"

def login_admin():
    session['admin_logged'] = 1

def isLogged():
    return True if session.get('admin_logged') else False

def logout_admin():
    session.pop('admin_logged', None)

@admin.route('/')
def index():
    if not isLogged():
        return redirect(url_for('.login'))
    total_users = Users.query.count()
    total_games = Games.query.count()
    today = datetime.now()
    last_week = today - timedelta(days=7)
    user_stats = (db.session.query(func.date(Users.time, 'unixepoch'), func.count())
                  .filter(Users.time >= int(last_week.timestamp()))
                  .group_by(func.date(Users.time, 'unixepoch'))
                  .all())
    game_stats = (db.session.query(func.date(Games.time, 'unixepoch'), func.count())
                  .filter(Games.time >= int(last_week.timestamp()))
                  .group_by(func.date(Games.time, 'unixepoch'))
                  .all())

    user_dates = [str(stat[0]) for stat in user_stats] if user_stats else []
    user_counts = [stat[1] for stat in user_stats] if user_stats else []
    game_dates = [str(stat[0]) for stat in game_stats] if game_stats else []
    game_counts = [stat[1] for stat in game_stats] if game_stats else []

    return render_template(
        'admin/index.html',
        menu=menu,
        title='Админ-панель',
        total_users=total_users,
        total_games=total_games,
        user_dates=user_dates,
        user_counts=user_counts,
        game_dates=game_dates,
        game_counts=game_counts
    )

#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для обновления сайта через админ-панель
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/update_site', methods=['POST'])
def update_site():
    if not isLogged():
        return redirect(url_for('.login'))

    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    try:
        print("Pulling from Git")
        repo = Repo('/home/faderi23m/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')  # Принудительно синхронизируем с origin/main
        print("Git pull successful")
        os.system('touch /var/www/faderi23m_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        flash("Сайт успешно обновлен", "success")
    except Exception as e:
        print(f"Error: {str(e)}")
        flash(f"Ошибка обновления сайта: {str(e)}", "error")

    return redirect(url_for('.index'))

#-----------------------------------------------------------------------------------------------------------------
"""
                                     Маршрут для обновления сайта через вебхук GitHub
"""
#-----------------------------------------------------------------------------------------------------------------
@admin.route('/webhook', methods=['POST'])
def webhook():
    print(f"Request received: {request.method} {request.headers.get('User-Agent')}")
    signature = request.headers.get('X-Hub-Signature-256')
    print(f"Signature: {signature}")
    if not signature:  # Если подписи нет, это не запрос от GitHub
        print("No signature provided")
        return 'No signature provided', 403

    secret = SECRET_KEY.encode('utf-8')
    hash_object = hmac.new(secret, request.data, hashlib.sha256)
    expected_signature = 'sha256=' + hash_object.hexdigest()
    print(f"Expected signature: {expected_signature}")
    if not hmac.compare_digest(expected_signature, signature):
        print("Invalid signature")
        return 'Invalid signature', 403

    try:
        print("Pulling from Git")
        repo = Repo('/home/faderi23m/flask_game_portal')
        repo.git.fetch('origin')
        repo.git.reset('--hard', 'origin/main')  # Принудительно синхронизируем с origin/main
        print("Git pull successful")
        os.system('touch /var/www/faderi23m_pythonanywhere_com_wsgi.py')
        print("WSGI file touched")
        return 'Updated successfully', 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

@admin.route('/login', methods=["POST", "GET"])
def login():
    if not isLogged():
        if request.method == "POST":
            if request.form['user'] == "testing" and check_password_hash(generate_password_hash(request.form['psw']), hash):
                login_admin()
                return redirect(url_for('.index'))
            else:
                flash('Неверная пара логин/пароль', 'error')
        return render_template('admin/login.html', title='Админ-панель(вход)')
    else:
        return redirect(url_for('.index'))

@admin.route('/logout', methods=['POST', 'GET'])
def logout():
    if not isLogged():
        return redirect(url_for('.login'))
    logout_admin()
    return redirect(url_for('.login'))

@admin.route('/listusers')
def listusers():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')
        filter_role = request.args.get('role', '')
        query = Users.query
        if search:
            query = query.filter((Users.name.ilike(f'%{search}%')) |
                                 (Users.email.ilike(f'%{search}%'))
                                 )
        if filter_role:
            query.filter(Users.role == filter_role)
        if sort == 'name_asc':
            query = query.order_by(asc(Users.name))
        elif sort == 'name_desc':
            query = query.order_by(desc(Users.name))
        elif sort == 'time_asc':
            query = query.order_by(asc(Users.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Users.time))
        else:
            query = query.order_by(desc(Users.time))
        users = query.all()
    except Exception as e:
        flash('Ошибка получения Пользователей' + str(e),message='error')
        users = []
    return render_template('admin/listuser.html', title='Список пользователей', menu=menu, list=users, search=search,sort=sort,filter_role=filter_role)

@admin.route('/list-games')
def listgames():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        search = request.args.get('search', '').strip()
        sort = request.args.get('sort', 'time_desc')
        filter_type = request.args.get('type', '')
        query = Games.query
        if search:
            query = query.filter((Games.title.ilike(f'%{search}%')) |
                                 (Games.description.ilike(f'%{search}%'))
                                 )
        if filter_type == 'link':
            query = query.filter(Games.link.like('http%'))
        elif filter_type == 'pygame':
            query = query.filter(Games.link.like('%'))
        if sort == 'title_asc':
            query = query.order_by(asc(Games.title))
        elif sort == 'title_desc':
            query = query.order_by(desc(Games.title))
        elif sort == 'time_asc':
            query = query.order_by(asc(Games.time))
        elif sort == 'time_desc':
            query = query.order_by(desc(Games.time))
        else:
            query = query.order_by(desc(Games.time))
        games=query.all()
    except Exception as e:
        flash('Ошибка получения игр' + str(e),'error')
        games = []
    return render_template('admin/listgames.html', title='Список игр', menu=menu, games=games, search=search, sort=sort, filter_type=filter_type)

@admin.route('/list-menu')
def listmenu():
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        menus=MainMenu.query.all()
    except Exception as e:
        flash('Ошибка получения игры' + str(e),'error')
        menus = []
    return render_template('admin/listmenus.html', title='Список пунктов меню', menu=menu, menus=menus)

@admin.route('/add_menu', methods=["POST", "GET"])
def addmenu():
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == "POST":
        title = request.form.get('title')
        url = request.form.get('url')

        if not title or not url:
            flash('Заполните все поля','error')
        else:
            try:
                new_menu = MainMenu(title=title,url=url)
                db.session.add(new_menu)
                db.session.commit()
                flash('Пункт меню добавлен',"succes")
                return redirect(url_for('.listmenu'))
            except Exception as e:
                print(f'Ошибка добавления в бд {e}')
                flash(f'Ошибка добавления в бд {e}','error')
    return render_template('admin/add_menus.html',menu = menu,title='Добавить пункт меню')

@admin.route('/add_game', methods=['POST', 'GET'])
def add_game():
    if not isLogged():
        return redirect(url_for('.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        game_type = request.form.get('game_type')
        cover_file = request.files.get('cover')

        if not title or not description or not cover_file:
            flash('Все поля должны быть заполнены', 'error')
        else:
            try:
                if Games.query.filter_by(title=title).first():
                    flash('Игра с таким название уже добавлена', 'error')
                    return render_template('admin/add_game.html', menu=menu, title='Добавить игру')
                cover_data = cover_file.read()
                new_game = Games(title=title, description=description, cover=cover_data)

                if game_type == 'link':
                    link = request.form.get('link')

                    if not link:
                        flash('Ссылка для внешней игры обязательна', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру')
                    if Games.query.filter_by(link=link).first():
                        flash('Игра с такой ссылкой уже добавлена', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру')


                    new_game.link = link
                elif game_type == 'pygame':
                    game_zip = request.files.get('game_zip')
                    screenshots_zip = request.files.get('screens_zip')
                    if not game_zip:
                        flash('Необходимо загрузить архив с игрой', 'error')
                        return render_template('admin/add_game.html', menu=menu, title='Добавить игру')

                    game_folder = secure_filename(title)
                    game_path = os.path.join('static/games', game_folder)
                    os.makedirs(game_path, exist_ok=True)

                    # Сохранение и разархивирование архива игры
                    game_zip_path = os.path.join(game_path, 'game.zip')
                    game_zip.save(game_zip_path)
                    with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            # Извлекаем имя файла без верхней папки
                            file_name = file_info.filename.split('/', 1)[1] if '/' in file_info.filename else file_info.filename
                            if file_name:  # Пропускаем пустые имена (например, корневые папки)
                                zip_ref.extract(file_info, game_path)
                                extracted_path = os.path.join(game_path, file_info.filename)
                                target_path = os.path.join(game_path, file_name)
                                if extracted_path != target_path:
                                    os.rename(extracted_path, target_path)
                    os.remove(game_zip_path)

                    # Сохранение и разархивирование скриншотов
                    if screenshots_zip:
                        screenshots_path = os.path.join(game_path, 'screenshots')
                        os.makedirs(screenshots_path, exist_ok=True)
                        screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                        screenshots_zip.save(screenshots_zip_path)
                        with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                            for file_info in zip_ref.infolist():
                                file_name = file_info.filename.split('/', 1)[1] if '/' in file_info.filename else file_info.filename
                                if file_name:
                                    zip_ref.extract(file_info, screenshots_path)
                                    extracted_path = os.path.join(screenshots_path, file_info.filename)
                                    target_path = os.path.join(screenshots_path, file_name)
                                    if extracted_path != target_path:
                                        os.rename(extracted_path, target_path)
                        os.remove(screenshots_zip_path)

                    new_game.link = game_folder

                db.session.add(new_game)
                db.session.commit()
                flash('Игра успешно добавлена', 'success')
                return redirect(url_for('.listgames'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка добавления игры: {str(e)}', 'error')
    return render_template('admin/add_game.html', menu=menu, title='Добавить игру')

@admin.route('/delete_user/<int:user_id>', methods=["POST", "GET"])
def deleteuser(user_id):
    if not isLogged():
        return redirect(url_for('login'))
    try:
        user = Users.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            flash('Пользователь удален','success')
        else:
            flash('Ошибка получения пользователя из бд','error')
    except Exception as e:
        db.session.rollback()
        print(f'Ошибка удаления пользователя {e}')
        flash(f'Ошибка удаления пользователя {e}', 'error')
    return redirect(url_for('.listusers'))

@admin.route('/delete_game/<int:game_id>', methods=["POST", "GET"])
def deletegame(game_id):
    if not isLogged():
        return redirect(url_for('login'))
    try:
        game = Games.query.get(game_id)
        if game:
            if game.link and not game.link.startswith('http'):
                game_folder = game.link.replace('/static/games/', '')
                game_path = os.path.join('/static/games', game_folder)
                if os.path.exists(game_path):
                    shutil.rmtree(game_path)
                    flash(f'Папка с игрой {game_folder} удалена', 'success')
                else:
                    flash(f'Папка с игрой {game_folder} не найдена', 'error')
            db.session.delete(game)
            db.session.commit()
            flash('Игра удалена','success')
        else:
            flash('Ошибка получения игры из бд','error')
    except Exception as e:
        db.session.rollback()
        print(f'Ошибка удаления игры {e}')
        flash(f'Ошибка удаления игры {e}', 'error')
    return redirect(url_for('.listgames'))

@admin.route('/delete_menu/<int:menu_id>', methods=["POST", "GET"])
def deletemenu(menu_id):
    if not isLogged():
        return redirect(url_for('login'))
    try:
        menu = MainMenu.query.get(menu_id)
        if menu:
            db.session.delete(menu)
            db.session.commit()
            flash('Игра удален','success')
        else:
            flash('Ошибка получения игры из бд','error')
    except Exception as e:
        db.session.rollback()
        print(f'Ошибка удаления игры {e}')
        flash(f'Ошибка удаления игры {e}', 'error')
    return redirect(url_for('.listmenu'))

@admin.route('/deletecomment/<int:comment_id>')
def deletecomment(comment_id):
    if not isLogged():
        return redirect(url_for('.login'))
    try:
        comment = Comments.query.filter_by(comment_id=comment_id)
        if comment:
            db.session.delete(comment)
            db.session.commit()
            flash('Коментарий удален', 'success')
        else:
            flash('Ошибка получения коментария', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления коментария {e}', 'error')
        print('Ошибка удаления коментария')
    return redirect(url_for('.listcomments'))

@admin.route('/edit-menu/<int:menu_id>', methods=['POST','GET'])
def editmenu(menu_id):
    if not isLogged():
        return redirect(url_for('.login'))
    menu_list = MainMenu.query.get(menu_id)
    if not menu_list:
        flash('Пункт меню не найден', 'error')
        return redirect(url_for('wlistmenu'))
    if request.method == "POST":
        title = request.form.get('title')
        url = request.form.get('url')
        if title or url:
            try:
                menu_list.title = title
                menu_list.url = url
                db.session.commit()
                flash('Пункт меню изменен',"succes")
                return redirect(url_for('.listmenu'))
            except Exception as e:
                print(f'Ошибка изменения {e}')
                flash(f'Ошибка изменения {e}','error')
    return render_template('admin/edit_mainmenus.html',menu = menu,title='Редактировать пункт меню', menu_list=menu_list)

@admin.route('/edit_game/<int:game_id>', methods=["POST", "GET"])
def edit_game(game_id):
    if not isLogged():
        return redirect(url_for('.login'))

    game = Games.query.get(game_id)
    if not game:
        flash("Игра не найдена", "error")
        return redirect(url_for('.listgames'))

    if request.method == "POST":
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        game_type = request.form.get('game_type')
        cover_file = request.files.get('cover')

        if title or description or (cover_file and cover_file.filename):
            if title and description:
                try:
                    if Games.query.filter_by(title=title).first():
                        flash('Игра с таким название уже добавлена', 'error')
                        return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру')
                    game.title = title
                    game.description = description

                    if cover_file and cover_file.filename:
                        cover_data = cover_file.read()
                        game.cover = cover_data

                    if game_type == 'link':
                        link = request.form.get('link')
                        if not link:
                            flash('Ссылка для внешней игры обязательна', 'error')
                            return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру')
                        if Games.query.filter_by(link=link).first():
                            flash('Игра с такой ссылкой уже добавлена', 'error')
                            return render_template('admin/edit_game.html', menu=menu, title='Редактировать игру')
                        game.link = link
                    elif game_type == 'pygame':
                        game_zip = request.files.get('game_zip')
                        screenshots_zip = request.files.get('screens_zip')
                        if game_zip:  # Обновляем только если загружен новый архив
                            game_folder = secure_filename(title)
                            game_path = os.path.join('static/games', game_folder)
                            os.makedirs(game_path, exist_ok=True)

                            game_zip_path = os.path.join(game_path, 'game.zip')
                            game_zip.save(game_zip_path)
                            with zipfile.ZipFile(game_zip_path, 'r') as zip_ref:
                                for file_info in zip_ref.infolist():
                                    file_name = file_info.filename.split('/', 1)[1] if '/' in file_info.filename else file_info.filename
                                    if file_name:
                                        zip_ref.extract(file_info, game_path)
                                        extracted_path = os.path.join(game_path, file_info.filename)
                                        target_path = os.path.join(game_path, file_name)
                                        if extracted_path != target_path:
                                            os.rename(extracted_path, target_path)
                            os.remove(game_zip_path)

                            if screenshots_zip:
                                screenshots_path = os.path.join(game_path, 'screenshots')
                                os.makedirs(screenshots_path, exist_ok=True)
                                screenshots_zip_path = os.path.join(screenshots_path, 'screenshots.zip')
                                screenshots_zip.save(screenshots_zip_path)
                                with zipfile.ZipFile(screenshots_zip_path, 'r') as zip_ref:
                                    for file_info in zip_ref.infolist():
                                        file_name = file_info.filename.split('/', 1)[1] if '/' in file_info.filename else file_info.filename
                                        if file_name:
                                            zip_ref.extract(file_info, screenshots_path)
                                            extracted_path = os.path.join(screenshots_path, file_info.filename)
                                            target_path = os.path.join(screenshots_path, file_name)
                                            if extracted_path != target_path:
                                                os.rename(extracted_path, target_path)
                                os.remove(screenshots_zip_path)

                            game.link = f'/static/games/{game_folder}'

                    db.session.commit()
                    flash("Игра успешно обновлена", "success")
                    return redirect(url_for('.listgames'))
                except Exception as e:
                    db.session.rollback()
                    flash(f"Ошибка обновления игры: {str(e)}", "error")
            else:
                flash("Все поля должны быть заполнены", "error")

    return render_template('admin/edit_game.html', menu=menu, title="Редактировать игру", game=game)
