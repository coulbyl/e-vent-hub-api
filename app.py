from dotenv import load_dotenv
import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from routes import ROUTES

from models.token import TokenBlockList
from models.admin import AdminModel
from models.organizer import OrganizerModel
from models.user import UserModel

load_dotenv(f"{os.getcwd()}/.env")

UPLOAD_FOLDER = f"{os.getcwd()}/uploads"

app = Flask(__name__)
CORS(app)

ACCESS_EXPIRES = timedelta(hours=1)

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# n'accepte que les demandes dont la taille ne dépasse pas 1 Mo.
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('FLASK_KEY')
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES

api = Api(app)


jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = TokenBlockList.find_by_jti(jti=jti)
    return token is not None


@jwt.user_identity_loader
def add_claims_to_jwt(identity):
    admin = AdminModel.find_by_uuid(_uuid=identity)
    organizer = OrganizerModel.find_by_uuid(_uuid=identity)
    client = UserModel.find_by_uuid(_uuid=identity)

    if admin and admin.role == 'superuser':
        return {'superuser': True, 'admin': False, 'organizer': False, 'client': False}
    elif admin and admin.role == 'admin':
        return {'superuser': False, 'admin': True, 'organizer': False, 'client': False}
    elif organizer:
        return {'superuser': False, 'admin': False, 'organizer': True, 'client': False}
    elif client:
        return {'superuser': False, 'admin': False, 'organizer': False, 'client': True}
    else:
        return {'superuser': False, 'admin': False, 'organizer': False, 'client': False}


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'description': 'The Token has expired.',
        'error': 'token_expired'
    }), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'description': 'Signature verication failed.',
        'error': 'invalid_token'
    }), 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'description': 'Request does not contain an access token.',
        'error': 'authorization_required'
    }), 401


@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return jsonify({
        'description': 'The Token is not fresh.',
        'error': 'fresh_token_required'
    }), 401


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'description': 'The Token has been revoked.',
        'error': 'token_revoked',
    }), 401


for route in ROUTES:
    api.add_resource(route['resource'], route['endpoint'])

if __name__ == '__main__':
    from db import db
    db.init_app(app)

    app.run(debug=os.getenv('DEBUG'))
