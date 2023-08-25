from flask import (
    Blueprint, request
)

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# found in the application page in the Developer Portal
PUBLIC_KEY = open('PUBLIC_KEY.txt').readlines()[0].strip()

VERIFY_KEY = VerifyKey(bytes.fromhex(PUBLIC_KEY))

# from flask_app.db import get_db

bp = Blueprint('interactions', __name__)

@bp.route('/interactions', methods=['POST'])
def interactions():
    signature = request.headers["X-Signature-Ed25519"]
    timestamp = request.headers["X-Signature-Timestamp"]
    body = request.data.decode("utf-8")

    try:
        VERIFY_KEY.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
    except BadSignatureError:
        return "invalid request signature", 401

    if request.json["type"] == 1:
        return {"type": 1}
    
@bp.route('/for-fun', methods=['GET'])
def for_fun():
    return "for fun"


