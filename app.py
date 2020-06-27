from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from flask import Flask, jsonify , request, json
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from functools import wraps
from bson import ObjectId

import datetime, jwt, os, json, re, operator
import current_user as current
import default_data as dflt
import mongodb as mongodb
import scan_engine

mongodb.connect_to_db()

app = Flask(__name__)
#app.config['MONGO_URI'] = 'mongodb+srv://Kristijan_10:Messi123@digitality-4hkuh.mongodb.net/digitality_production?retryWrites=true&w=majority'
app.config['MONGO_URI'] = 'mongodb+srv://admin:admin@cluster0-5uwqu.mongodb.net/test?retryWrites=true&w=majority'


mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app, resources={r"/*": {"origins": "*"}})

def token_required(f):
    # Stack Abuse, Single Page Apps with Vue.js and Flask: JWT Authentication, Adam McQuistan
    # https://stackabuse.com/single-page-apps-with-vue-js-and-flask-jwt-authentication/
    @wraps(f)
    def _verify(*args, **kwargs):
        auth_headers = request.headers.get('Authorization', '').split()
        
        invalid_msg = {
            'message': 'Invalid token. Registeration and / or authentication required',
            'authenticated': False
        }
        expired_msg = {
            'message': 'Expired token. Reauthentication required.',
            'authenticated': False
        }

        if len(auth_headers) != 2:
            return jsonify(invalid_msg), 401

        try:
            token = auth_headers[1]
            data = jwt.decode(token, os.getenv("JWT_SECRET"))
            user = mongodb.get_user(data['sub'])
            
            if not user:
                raise RuntimeError('User not found')
            elif not current.user:
                current.user = user
                
            del user['password']
            del user['_id']                
                
            return f(user, *args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            current.user = {}
            return jsonify(expired_msg), 401
        
    return _verify

@app.route('/')
def index():
    return "Hello World"

@app.route('/register', methods=['POST'])
def register():
    doc = request.get_json()
    
    user = {
        '_id': str(ObjectId()),
        'name': doc['name'],
        'surname': doc['surname'],
        'email': doc['email'],
        'password': bcrypt.generate_password_hash(doc['password'], 8),
        'personal_archive_id': None,
        'archive_ids': None,        
        'alias_list': [],
        'email_list': []
    }
    
    res = mongodb.register_user(user)
    return jsonify(res)


@app.route('/login', methods=['POST'])
def login():
    email = request.get_json()['email']
    password = request.get_json()['password']
    
    user = mongodb.get_user(email)
    
    if (user and user['password']) and (bcrypt.check_password_hash(user['password'], password)):
        del user['password']
        del user['_id']

        token_data = {
            'sub': user['email'],
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }
        
        user['token'] = jwt.encode(token_data, os.getenv("JWT_SECRET"), algorithm='HS256').decode("utf-8")
    
    return jsonify(user)


@app.route('/GetArchives', methods=['POST'])
def getarhive():
    user = mongodb.get_user(request.get_json()['email'])
    
    if not user:
        return jsonify(False)
    
    archive_ids = user['archive_ids']
    archives = list(mongodb.get_archives(archive_ids))
    
    if not archives:
        return jsonify(False)

    return jsonify(archives)


@app.route('/send_document', methods=['POST'])
@token_required
def sendDocument(cur_user):
    doc_url = request.get_json()['doc_url']
    doc_data = scan_engine.photo_to_dict(doc_url)

    return jsonify(doc_data)


@app.route('/search/lista_arhiva', methods=['POST'])
@token_required
def searchArchives(cur_user):
    result = mongodb.get_archives( request.get_json()['archive_ids'] )
    searchTerm = str(request.get_json()['searchTerm']).lower()
    
    if not searchTerm:
        return jsonify(result)
    
    currentArchive_id = request.get_json()['currentArchive_id']
    cur_arc = mongodb.get_one_archive(currentArchive_id)
    
    regex = re.compile('^(%s)' % searchTerm)
    subarchives = [sub_arc for sub_arc in cur_arc['subarchives'] if regex.match(sub_arc['name'].lower()) ] 
    
    for archives in result:
        if archives['_id'] == currentArchive_id:
            archives['subarchives'] = subarchives

    return jsonify(result)


@app.route('/archives/createSubarchive', methods=['POST'])
@token_required
def createSubarchive(cur_user):
    archive_name = request.get_json()['archive_name'].lower()
    personal_archive_id = request.get_json()['personal_archive_id']
    subarchive_id = str(ObjectId())
    
    mongo.db.archives.update({'_id': personal_archive_id},{'$push':{
        'subarchives': {
            'subarchive_id': subarchive_id,
            'name': archive_name,
            'last_used': datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'documents': []
        }}})
        
    return "Dodano"

@app.route('/archive/deleteSubarchive', methods=['PATCH'])
@token_required
def deleteSubarchive(cur_user):
    doc = request.get_json()
        
    if cur_user['personal_archive_id'] == doc['personal_archive_id']:
        res = mongodb.delete_subarchive(doc['personal_archive_id'], doc['subarchive_id'])
        return jsonify(res)
    else:
        return jsonify(False)


@app.route('/archive/UpdateExaminationDate', methods=['POST'])
@token_required
def update_examination_date(cur_user):
    res = mongodb.update_examination_time(request.get_json())
    
    return jsonify(res)


@app.route('/archives/SortArchives', methods=['POST'])
@token_required
def sortArchives(cur_user):

    if (mongo.db.archives.count() == 0):
        provjera = False
        return jsonify(provjera)

    else:
        doc = request.get_json()
        result = []
        subarchives = []

        if(doc['sorttype'] == 'abecedno_uzlazno' or doc['sorttype'] == 'datum_pregleda_uzlazno'): ascORdes = False
        else: ascORdes = True
        if(doc['sorttype'] == 'abecedno_uzlazno' or doc['sorttype'] == 'abecedno_silazno'): sortby = "name"
        else: sortby = "last_used"

        for archives in mongo.db.archives.find({'_id': {'$in':doc['archive_ids']}}):
            result.append(archives)

        for archives in mongo.db.archives.find():
            if(archives['_id'] == doc['currentArchive_id']):
                for sub in archives['subarchives']:
                    subarchives.append(sub)

        subarchives.sort(key=operator.itemgetter(sortby),reverse=ascORdes)
        
        for archives in result:
            if(archives['_id'] == doc['currentArchive_id']):
                archives['subarchives'] = subarchives

        return jsonify(result)


@app.route('/archives/share', methods=['POST'])
@token_required
def share_archive(cur_user):
    new_email = request.get_json()['email']
    
    if new_email in cur_user['email_list']: return jsonify(False)

    new_user = mongodb.get_user(new_email)
    if not new_user: return jsonify(False)
    
    res = mongodb.share_archive(cur_user, new_user)
    
    return jsonify(res)


@app.route('/archives/shareDelete', methods=['PATCH'])
@token_required
def delete_shared_archive(cur_user):
    foreign_email = request.get_json()['foreign_email']
    
    res = mongodb.remove_sharing(cur_user, foreign_email)
    return jsonify(res)


@app.route('/addAlias', methods=['PUT'])
@token_required
def add_alias(cur_user):
    new_alias = request.get_json()
    res = mongodb.add_alias(new_alias, cur_user['email'])
    
    return jsonify(res)


@app.route('/deleteAlias', methods=['PATCH'])
@token_required
def delete_alias(cur_user):
    alias = request.get_json()
    res = mongodb.delete_alias(alias['oib'], cur_user['email'])

    return jsonify(res)


@app.route('/addDocumentToDatabase', methods=['POST'])
@token_required
def add_doc_to_database(cur_user):
    doc = request.get_json()
    scan_engine.add_to_database(doc['personal_archive_id'], doc['document'])

    return "Dodano"


@app.route('/changeArchiveName', methods=['POST'])
@token_required
def change_archive_name(cur_user):
    doc = request.get_json()
    
    res = mongodb.change_arc_name(doc['archive_id'], doc['archive_name'])
    return jsonify(res)


@app.route('/getCompanyData', methods=['POST'])
@token_required
def get_company_data(cur_user):
    oib = request.get_json()['company_oib']
    companyData = mongodb.get_company(oib)

    return jsonify(companyData)


@app.route('/update_document', methods=['PATCH'])
@token_required
def update_document(cur_user):
    archive_id = request.get_json()['archive_id']
    document = request.get_json()['document']

    res = mongodb.update_document(archive_id, document)
    
    return jsonify(res)


@app.route('/delete_document', methods=['PATCH'])
@token_required
def delete_document(cur_user):
    archive_id = request.get_json()['archive_id']
    document = request.get_json()['document']

    res = mongodb.delete_document(archive_id, document)
    
    return jsonify(res) 


@app.route('/delete_user', methods=['POST'])
@token_required
def delete_user(cur_user):
    sent_password = request.get_json()['sent_password']
    saved_password = mongodb.get_user(cur_user['email'])['password']
    
    if(bcrypt.check_password_hash(saved_password, sent_password)):
        res = mongodb.delete_user(cur_user['email'])
        return jsonify(res)
    
    return jsonify(False)

if __name__ == "__main__":
    app.run(port=5000, debug=True)