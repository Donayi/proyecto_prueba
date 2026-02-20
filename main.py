from datetime import date
from http import HTTPStatus

from dotenv import load_dotenv
import os

from flask import Flask, request, Blueprint
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import InvalidRequestError

from marshmallow import Schema, fields, ValidationError, validate

load_dotenv()

app = Flask(__name__)
# Configuramos la cadena de conexión de base de datos
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
# Creamos una instancia de la bd para realizar operaciones
db = SQLAlchemy(app)

# Agregamos ruta general para personas
person_bp = Blueprint('person', __name__, url_prefix='/persons')

# creamos el modelo comforme a la tabla y columnas
class Persona(db.Model):
    __tablename__ = 'personas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(120), nullable=False)
    edad = db.Column(db.Integer, nullable=True)
    correo_electronico = db.Column(db.String(120), nullable=False, unique=True)
    url = db.Column(db.String(120), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    es_activo = db.Column(db.Boolean, default=True)

# Definimos el esquema con el que vamos a validar la entrada en JSON y serializar el objeto de salida
class PersonaSchema(Schema):
    id = fields.Integer(dump_only=True)
    nombre = fields.String(
        required=True,
        validate=[
            validate.Regexp(r'^[A-Z][a-z]+(?: [A-Z][a-z]+)*$',
                            error="El apellido debe iniciar con mayúscula y contener solo letras."),
            validate.Length(min=3, error="El apellido debe tener al menos 3 caracteres."),
        ],
    )

    apellido = fields.String(required=True)

    categoria = fields.String(
        required=True,
        validate=[
            validate.OneOf(["A", "B", "C", "D", "E", "F"]),
        ]
    )

    edad = fields.Integer(
        required=False,
        validate=[
            validate.Range(min=18, error="Debe ser mayor de edad"),
            validate.Range(max=50, error="No debe ser una persona mayor de edad")
        ]
    )
    correo_electronico = fields.Email(required=True)
    url = fields.URL(required=True)

    fecha_nacimiento = fields.Date(
        required=False,
        validate=[
            validate.Range(max=date.today(), error='La fecha de nacimiento no puede ser futura'),
        ]
    )
    #es_activo = fields.Boolean()

persona_schema = PersonaSchema()

@person_bp.post("")
def create_person():
    try:
        # Validar datos entrada de la petición (comforme al esquema)
        data = persona_schema.load(request.json)
    except ValidationError as e:
        # Si la validación es incorrecta genera respuesta de error
        return e.messages, HTTPStatus.BAD_REQUEST

    # Creamos el objeto con los datos obtenidos del JSON
    person = Persona(**data)
    # Insertamos el registro en base de datos
    db.session.add(person)
    # Confirmamos los cambios en bd
    db.session.commit()

    # renderizar salida del registro en formato JSON
    return persona_schema.dump(person), HTTPStatus.CREATED

@person_bp.get("")
def get_all_persons():
    try:
        # query param
        # consultar todos los registros con un filtro (ejemplo: /persons?edad=34&nombre=Luis)
        personas = Persona.query.filter_by(**request.args).all()
    except InvalidRequestError as e:
        # Si hay algun error de bd se devuelve mensaje de error
        return {"message": str(e)}
    # Renderizamos todos los registros consultados en formato JSON
    return persona_schema.dump(personas, many=True), HTTPStatus.OK

@person_bp.get("/<int:id>")
def get_person_by_id(id: int): # path param
    # Consultar un solo registro por id
    persona = Persona.query.get_or_404(id)
    # renderizar salida del registro en formato JSON
    return persona_schema.dump(persona), HTTPStatus.OK

@person_bp.put("/<int:id>")
def update_person(id: int):

    try:
        # Validar datos entrada de la petición (comforme al esquema)
        data = persona_schema.load(request.json, partial=True)
    except ValidationError as e:
        return e.messages, HTTPStatus.BAD_REQUEST

    # consultar el registro en base de datos
    persona = Persona.query.get_or_404(id)

    # Actualizar cada campo con los datos de la peticion
    for key, value in data.items():
        setattr(persona, key, value)

    # comfirmar los cambios
    db.session.commit()
    return persona_schema.dump(persona), HTTPStatus.OK

@person_bp.delete("/<int:id>")
def delete_person(id: int):
    persona = Persona.query.get_or_404(id)
    db.session.delete(persona)
    db.session.commit()
    return "", HTTPStatus.NO_CONTENT

@person_bp.errorhandler(404)
def page_not_found(e):
    # Capturar cada error cuando no se encuentra el registro
    return {"message": "Persona no encontrada"}, HTTPStatus.NOT_FOUND

app.register_blueprint(person_bp)

app.run()
