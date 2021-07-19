from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
from app.models import User, Enterprise
from app import nyse_symbols, logging
from app import app
import re

class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember_me = BooleanField("Recuérdame")
    submit = SubmitField("Ingresar")


class RegistrationForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    email = StringField("Correo electrónico", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    password2 = PasswordField(
        "Repetir contraseña", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Registarse")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Por favor usa un nombre de usuario diferente.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Por favor usa una direccion de correo diferente.")


class EditProfileForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    about_me = TextAreaField("Acerca de mi", validators=[Length(min=0, max=140)])
    submit = SubmitField("Enviar")

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError("Por favor usa un nombre de usuario diferente.")


class ValueListField(StringField):
    """Stringfield for a list of separated values"""

    def __init__(self, label='', validators=None, remove_duplicates=True, to_lowercase=True, separator=' ', **kwargs):
        """
        Construct a new field.
        :param label: The label of the field.
        :param validators: A sequence of validators to call when validate is called.
        :param remove_duplicates: Remove duplicates in a case insensitive manner.
        :param to_lowercase: Cast all values to lowercase.
        :param separator: The separator that splits the individual tags.
        """
        super(ValueListField, self).__init__(label, validators, **kwargs)
        self.remove_duplicates = remove_duplicates
        self.to_lowercase = to_lowercase
        self.separator = separator
        self.data = []

    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(self.separator)]
            if self.remove_duplicates:
                self.data = list(self._remove_duplicates(self.data))
            if self.to_lowercase:
                self.data = [x.lower() for x in self.data]

    @classmethod
    def _remove_duplicates(cls, seq):
        """Remove duplicates in a case insensitive, but case preserving manner"""
        d = {}
        for item in seq:
            if item.lower() not in d:
                d[item.lower()] = True
                yield item


class EnterpriseForm(FlaskForm):
    name = TextAreaField("Nombre de la empresa", validators=[DataRequired(), Length(min=1, max=64)])
    description = TextAreaField(
        "Descripción de la empresa", validators=[DataRequired(), Length(min=1, max=140)]
    )
    symbol = TextAreaField(
        "Símbolo de la empresa", validators=[DataRequired(), Length(min=1, max=10)]
    )
    values = ValueListField(
        "Valores separados por coma",
        separator=",",
        validators=[Length(max=10, message="Sólo se pueden tener hasta 10 valores.")]
    )
    submit = SubmitField("Agregar")

    def validate_symbol(self, symbol):
        app.logger.error(symbol.data)
        app.logger.error(nyse_symbols)
        if symbol.data in nyse_symbols:
            raise ValidationError("El símbolo de tu empresa ya está registrado en la bolsa de valores de Nueva York")
        enterprise = Enterprise.query.filter_by(symbol=self.symbol.data).first()
        if enterprise is not None:
            raise ValidationError("Símbolo ya usado. Por favor usa un símbolo diferente.")
        if re.match(r'\b[A-Z]{3}\b[.!?]?', str(symbol.data)) is None:
             raise ValidationError("Símbolo no sigue la expresión regular usada por el NYSE.")


    def validate_name(self, name):
        enterprise = Enterprise.query.filter_by(name=self.name.data).first()
        if enterprise is not None:
            raise ValidationError("Por favor usa un nombre diferente.")