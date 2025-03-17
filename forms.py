from flask_wtf import FlaskForm, RecaptchaField
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, BooleanField, PasswordField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from db import Users
import re

class LoginForm(FlaskForm):
    email = StringField('Email: ', validators=[Email(message='Некорректный email')])
    psw = PasswordField('Пароль: ', validators=[DataRequired(),
                                                Length(min=4, max=100, message='Пароль должен быть от 4 до 100 сиволов')])
    remember = BooleanField('Запомнить', default=False)
    submit = SubmitField('Войти', render_kw={'class' : 'login_button'})

class RegisterForm(FlaskForm):
    name = StringField('Имя:', validators=[Length(min=4, max=100, message='Имя должно быть от 4 до 100 символов')])
    email = StringField('Email: ', validators=[Email(message='Некорректный email')])
    psw = PasswordField('Пароль: ', validators=[DataRequired(),
                                                Length(min=4, max=100, message='Пароль должен быть от 4 до 100 сиволов')])
    psw2 = PasswordField('Повтор пароля:', validators=[DataRequired(), EqualTo('psw', message="Пароли не совпадают")])
    recaptcha = RecaptchaField()
    submit = SubmitField('Регистрация', render_kw={'class' : 'login_button'})

    def validate_name(self,field):
        if field.data and field.data != '':
            if not re.match(r'[a-zа-яA-ZА-Я0-9\s]+$', field.data):
                raise ValidationError('Имя может включать только буквы, цифры и пробелы')

    def validate_email(self,field):
        if Users.query.filter_by(email=field.data).first():
            raise ValidationError('Пользователь с таким email уже имеется')

class EditProfileForm(FlaskForm):
    name = StringField('Имя:', validators=[Length(min=4, max=100, message='Имя должно быть от 4 до 100 символов'), Optional()])
    email = StringField('Email: ', validators=[Email(message='Некорректный email'), Optional()])
    password = PasswordField('Новый пароль: ', validators=[Optional()])
    password_confirm = PasswordField('Повтор нового пароля:', validators=[EqualTo('password', message="Пароли не совпадают"), Optional()])
    avatar = FileField('Новый аватар', validators=[FileAllowed(["png", "PNG", "gif", "GIF", "jpg", "jpeg","jfif"],
                                                               'Разрешены только изображения формата png, gif, jpg, jpeg, jfif, GIF, PNG')])
    submit = SubmitField('Сохранить', render_kw={'class': 'btn btn-success'})

    def validate_name(self,field):
        if field.data and field.data != '':
            if not re.match(r'[a-zа-яA-ZА-Я0-9\s]+$', field.data):
                raise ValidationError('Имя может включать только буквы, цифры и пробелы.')

    def validate_email(self,field):
        from flask_login import current_user
        if field.data and field.data != '':
            if Users.query.filter(Users.email == field.data, Users.id != current_user.get_id()).first():
                raise ValidationError('Пользователь с таким email уже имеется.')