from pymongo import MongoClient
from datetime import datetime, timedelta

import bcrypt
import json
from bson import ObjectId

import default_data as dflt
import current_user as current 

# CONNECTION ########################################################
db = None

def connect_to_db():
    try:
        #cluster = MongoClient("mongodb+srv://Kristijan_10:Messi123@digitality-4hkuh.mongodb.net/digitality_production?retryWrites=true&w=majority")
        cluster = MongoClient("mongodb+srv://admin:admin@cluster0-5uwqu.mongodb.net/test?retryWrites=true&w=majority")
        
        global db
        db = cluster["digitality_production"]
        
        index_email()
        return db
    
    except:
        print("Failed to connect to the database!")
        return None 
    
def index_email():
    collection = db["users"]
    collection.create_index([ ("email", -1) ], unique=True)


# COMPANY ###########################################################
def add_new_company(data):
    collection = db["Company"]
    data['_id'] = str(ObjectId())
    
    try:
        collection.insert(data)
    except:
        print("add_new_company() - failed to add new company!")
        return False
    
    return True

def get_company(oib):
    collection = db["Company"]
    return collection.find_one({'oib': oib})

def update_company(company_data): 
    collection = db["Company"]
    
    try:
        collection.find_one_and_replace({'_id': company_data['_id']}, company_data)   
    except:
        print("update_company() - failed to find and replace the document!")
        return False
    
    return True


# ARCHIVE ###########################################################
def get_archives(archive_ids):
    collection = db["archives"]
    
    filter = {'_id': {'$in':archive_ids}}
    
    try:
        arc = list(collection.find(filter))
    except:
        print("get_archives() - failed to get archives!")
        arc = None
        
    return arc

def get_one_archive(archive_id):
    collection = db["archives"]
    
    filter = {'_id': archive_id}
    try:
        arc = collection.find_one(filter)  
    except:
        print("get_one_archive() - failed to get archive!")
        arc = None
        
    return arc

def delete_archive(arc_id):
    collection = db["archives"]
    
    filter = {'_id': arc_id}

    try:
        collection.delete_one(filter)
        return True    
    except:
        print("delete_archive() - failed to delete archive!")
        return False
     
def change_arc_name(arc_id, new_name):
    collection = db["archives"]
    
    try:
        collection.update_one(
            {'_id': arc_id},
            {'$set': {'name': new_name} }
        )
        return True
    except:
        print("change_arc_name() - failed to delete archive!")
        return False
    
    
# SUBARCHIVE ########################################################
def get_subarchive(arc, subarchive_name):
    for index, subarchive in enumerate(arc['subarchives']):
        if subarchive_name == subarchive['name']:
            return (index, subarchive)
        
    return (None, dflt.get_subarchive(subarchive_name))

def update_subarchive(arc_id, document):
    collection = db["archives"]
    
    filter = {'_id': arc_id}
    update = {'$set': {'subarchives': document}}
    
    try:
        collection.update_one(filter, update)   
    except:
        print("update_subarchive() - failed to update document!")
        return False
    
    return True  

def update_examination_time(ids):
    arc = get_one_archive(ids['cur_arc'])
    if not arc: return False
    index, subarchive = get_subarchive(arc, ids['sub_arc'])
    
    subarchive['last_used'] =  datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    arc['subarchives'][index] = subarchive
    
    return update_subarchive(ids['cur_arc'], arc['subarchives'])

def delete_subarchive(arc_id, subarc_id):
    collection = db["archives"]
    
    filter = {'_id': arc_id}
    update = {
        '$pull':{'subarchives':{'subarchive_id': subarc_id}}
    }
    
    try:
        collection.update(filter, update)
    except:
        print("delete_subarchive() - failed to delete subarchive")
        return False
    
    return True


# DOCUMENTS #########################################################
def create_document(arc_id, document):
    arc = get_one_archive(arc_id)
    if not arc: return False
    index, subarchive = get_subarchive(arc, document['naziv_dobavljaca'])
    
    document['id_dokumenta'] = str(ObjectId())
    
    subarchive['documents'].append(document)
    if index:
        arc['subarchives'][index] = subarchive
    else:
        arc['subarchives'].append(subarchive)
    
    return update_subarchive(arc_id, arc['subarchives'])

def update_document(arc_id, document):
    arc = get_one_archive(arc_id)
    if not arc: return False
    index, subarchive = get_subarchive(arc, document['naziv_dobavljaca'])
    
    # FIND AND REPLACE DOC IN LIST
    for idx, doc in enumerate(subarchive['documents']):
        if doc['id_dokumenta'] == document['id_dokumenta']:
            subarchive['documents'][idx] = document
            break
      
    arc['subarchives'][index] = subarchive
    
    return update_subarchive(arc_id, arc['subarchives'])

def delete_document(arc_id, document):
    arc = get_one_archive(arc_id)
    if not arc: return False
    index, subarchive = get_subarchive(arc, document['naziv_dobavljaca'])
    
    filtered_subarchive = [cur_doc for cur_doc in subarchive['documents'] if cur_doc['id_dokumenta'] != document['id_dokumenta']]
    subarchive['documents'] = filtered_subarchive
    
    arc['subarchives'][index] = subarchive
    
    return update_subarchive(arc_id, arc['subarchives']) 


# USER ##############################################################
def register_user(user): 
    user_collection = db["users"]
    arc_collection = db["archives"]
    
    default_arc = dflt.get_default_arc()

    user['archive_ids'] = [str(default_arc['_id'])]
    user['personal_archive_id'] = str(default_arc['_id'])
    
    try:
        user_collection.insert(user)
    except:
        print("Failed to insert user!")
        return False
    
    try:
        arc_collection.insert(default_arc)
    except:
        print("Failed to insert archive!")
        user_collection.delete_one({'_id': user['_id']}) # Ako je user insertan a archive nije, obrisi usera
        return False
    
    return True

def get_user(email):  
    collection = db["users"]
    
    if collection.count == 0:
        return False

    return collection.find_one({'email': email})

def delete_user(email):
    collection = db["users"]
    user = get_user(email)
    
    try:
        collection.delete_one({'email': user['email']})
    except:
        print("Failed to delete user!")
        return False
    
    try:
        delete_archive(user['personal_archive_id'])
    except:
        print("Failed to delete personal archive of deleted user!")
    
    return True

def add_alias(alias, email):
    collection = db["users"]
    
    try:
        collection.update_one(
            {'email': email},
            {'$push': {'alias_list': alias}}
        )
    except:
        print('add_alias() - cannot add alias!')
        return False
    
    return True

def delete_alias(alias_oib, email): 
    collection = db["users"]
    
    try:
        collection.update_one(
            {'email': email},
            {'$pull': {'alias_list': {'oib': alias_oib }}}
        )
    except:
        print('delete_alias() - cannot delete alias!')
        return False
    
    return True

def share_archive(cur_user, new_user):
    collection = db["users"]
    
    try:
        collection.update_one(
            {'email': new_user['email']},
            {'$push': {'archive_ids': cur_user['personal_archive_id']} }
        )

        collection.update_one(
            {'email': cur_user['email']},
            {'$push': {'email_list': new_user['email']} }
        )
        return new_user['email']
    except:
        print("share_archive() - failed to update records!")
        return False

def remove_sharing(cur_user, foreign_email):
    collection = db["users"]
    
    try:
        collection.update_one(
            {'email': foreign_email},
            {'$pull': {'archive_ids': cur_user['personal_archive_id']} }
        )

        collection.update_one(
            {'email': cur_user['email']},
            {'$pull': {'email_list': foreign_email} }
        )
        
        return True
    except:
        print("remove_sharing() - failed to update records!")
        return False


# TESTING ###########################################################
def test_add_new_doc(test_archive_id):
    document = {
        'meta_data': {
            'added_by': 'jane@doe.com',
            'added_on': '01/01/2020',
            'added_at': '12:00'
        },
        'id_dokumenta': '5edfa361c509ffb1cf2ea928',
        'naziv_dobavljaca': 'Company C',
        'oib_dobavljaca': '16942983514',
        'iban_primatelja': 'HR012329671212',    
        
        'naziv_kupca': 'John Doe',
        'oib_kupca': '32145678901',
        'iban_platitelja': 'HR321456789012',
        
        'mjesto_izdavanja': 'Zagreb',
        'datum_izdavanja': '01/01/2020',
        'datum_dospijeca': '01/02/2020',
        
        'broj_racuna': 'user_input',
        'poziv_na_broj': 'user_input',
        'vrsta_usluge': 'Struja',
        'iznos': '100kn'
    }
    
    res = create_document(test_archive_id, document)
    if res:
        print("test_add_new_doc - success")
    else:
        print("test_add_new_doc - fail")
    
def test_update_doc(test_archive_id):
    document = {
        'meta_data': {
            'added_by': 'jane@doe.com',
            'added_on': '01/01/2020',
            'added_at': '12:00'
        },
        'id_dokumenta': '5edfa361c509ffb1cf2ea928',
        'naziv_dobavljaca': 'Company C',
        'oib_dobavljaca': '16942983514',
        'iban_primatelja': 'HR012329671212',    
        
        'naziv_kupca': 'John Doe',
        'oib_kupca': '32145678901',
        'iban_platitelja': 'HR321456789012',
        
        'mjesto_izdavanja': 'Zagreb',
        'datum_izdavanja': '01/01/2020',
        'datum_dospijeca': '01/02/2020',
        
        'broj_racuna': 'user_input',
        'poziv_na_broj': 'user_input',
        'vrsta_usluge': 'Struja',
        'iznos': '900kn'
    }
    
    res = update_document(test_archive_id, document)
    if res:
        print("test_update_doc - success")
    else:
        print("test_update_doc - fail")    

def test_delete_arc(test_archive_id):
    res = delete_archive(test_archive_id)
    if res:
        print("test_delete_arc - success")
    else:
        print("test_delete_arc - fail")

def test_delete_doc(test_archive_id, id_dokumenta):
    document = {
        'id_dokumenta': id_dokumenta,
        'naziv_dobavljaca': 'primjer'
    }
    
    res = delete_document(test_archive_id, document)
    if res:
        print("test_delete_doc - success")
    else:
        print("test_delete_doc - fail")
            
def test_delete_user(test_email):
    res = delete_user(test_email)
    if res:
        print("test_delete_user - success")
    else:
        print("test_delete_user - fail")
        
def test_update_user(): 
    res = update_user(user)
    if res:
        print("test_update_user - success")
    else:
        print("test_update_user - fail")
        
def test_add_alias(test_email):
    alias = {
        'ime': 'John',
        'prezime': 'Smith',
        'oib': '12345678901',
        'iban': 'HR123456789012',
        'postal_code': '10000',
    }
          
    res = add_alias(alias, test_email)
    if res:
        print("test_add_alias - success")
    else:
        print("test_add_alias - fail")

def test_delete_alias(test_email):
    alias = {
        "ime" : "John",
        "prezime" : "Smith",
        "oib" : "12345678901",
        "iban" : "HR123456789012",
        "postal_code" : "10000"
    }
    
    res = delete_alias(alias['oib'], test_email)
    if res:
        print("test_delete_alias - success")
    else:
        print("test_delete_alias - fail")
        
def test_share_archive():
    cur_user = {
        'email': 'e@mail.com',
        'personal_archive_id': '5ef4ba52f958cb0b5cf5b789'
    }
    new_user = {'email': 'e@mail2.com'}
    
    res = share_archive(cur_user, new_user)
    
    if res:
        print("test_share_archive - success")
    else:
        print("test_share_archive - fail")
    
    
if __name__ == "__main__":
    connect_to_db()
    
    test_share_archive()
    """
    test_archive_id = 1
    id_dokumenta = 3
    test_email = "e@mail2.com"
    
    # Add
    test_add_alias(test_email)
    test_add_new_doc(test_archive_id)
    
    # Update
    #test_update_user()
    test_update_doc(test_archive_id)
    
    # Delete
    test_delete_doc(test_archive_id, id_dokumenta)
    test_delete_arc(test_archive_id)
    
    test_delete_alias(test_email)
    test_delete_user(test_email)
    """