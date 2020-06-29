import mongodb as db
import current_user as current
import json

# IBAN ##########################################
def compare_possible_ibans(iban, company_data):
    # possible_ibans - iban brojevi koji se nisu pojavili dovoljno puta da bi se smatrali validnima
    try:
        possible_ibans = company_data['possible_ibans'] # okida try/except
        
        boundary = 5 
        upgrade_index = -1
        is_found = False
        
        for index, cur_iban in enumerate(possible_ibans):
            if cur_iban[1] == iban: 
                cur_iban[0] += 1
                is_found = True
                
                if cur_iban[0] >= boundary:
                    upgrade_index = index
                else:
                    possible_ibans[index] = cur_iban
                    
                break
        
        if not is_found:
            new_iban = [1, iban]
            company_data['possible_ibans'].append(new_iban)  
        
        elif upgrade_index != -1:
            new_iban = possible_ibans.pop(upgrade_index)
            company_data['iban'].append(new_iban)
    
    except:
        # ako ne postoji possible_ibans, stvori ga
        company_data['possible_ibans'] = [[1, iban]] 
            
    return company_data   
                   
def update_company_iban(iban, company_data):
    company_ibans = company_data['iban'] # format: company_ibans = [[broj_pojava, iban], [3, HR012345678512]]
    
    is_found = False
    # Pronadi iban i povecaj ucestalost za +1
    for index, cur_iban in enumerate(company_ibans):
        if cur_iban[1] == iban:
            company_ibans[index][0] += 1
            is_found = True
            break
    
    # Ako ne pronades, pretrazi u mogucim iban brojvima
    if not is_found:
        company_data = compare_possible_ibans(iban, company_data)

    company_ibans = sorted(company_ibans, key = lambda sub_list: sub_list[0])
    db.update_company(company_data)
    
    return company_data

def compare_user_iban(iban_list):
    user = current.user
    
    aliases = user['alias_list']
    alias_ibans = [alias['iban'] for alias in aliases]

    for index, iban in enumerate(iban_list):
        if iban in alias_ibans:
            iban_list.pop(index)
            break

    return iban_list    

def check_iban(iban_list, company_data):
    try:
        company_ibans = [iban[1] for iban in company_data['iban']]  # format: company_ibans = [[broj_pojava, iban], [3, HR012345678512]]
        if not iban_list: 
            print("ERROR! - No iban found from scanning, returning most used one!")
            return company_ibans[0]
    except TypeError:
        if not iban_list: 
            print("ERROR! - No company data found, nothing will be returned!")   
            return None
        else: return iban_list[0]
        
    if len(iban_list) == 1: return iban_list[0]
        
    # Standardno pretrazivanje   
    for iban in iban_list:
        if iban in company_ibans:
            return iban
    
    # Ako nije do sad pronadeno
    iban_list = compare_user_iban(iban_list)
    if len(iban_list) >= 1:
        iban = iban_list[0]
    else: 
        iban = company_ibans[0]
            
    return iban       
   #
# POSTANSKI BROJ ###########################
def get_pc_dict():
    try:
        with open('postal_codes.json', 'r') as fp:
            data = json.load(fp)
    except FileNotFoundError:
        data = None
        
    return data
               
def check_pc_dict(p_codes):
    pc_dict = get_pc_dict()
    
    result = None 
    # try/catch zbog mogucih junk podataka
    for pc in p_codes:
        try:
            result = pc_dict[pc]
            break
        except KeyError:
            continue
    
    return result

def check_user_pc(p_codes):
    user = current.user 
    
    aliases = user['alias_list']
    alias_codes = [alias['postanski_broj'] for alias in aliases]

    for index, p_code in enumerate(p_codes):
        if p_code in alias_codes:
            p_codes.pop(index)
            break
    
    return p_codes

def check_postal_code(p_codes):
    p_codes = [str(pc) for pc in p_codes]
    
    if len(p_codes) > 1:
        p_codes = check_user_pc(p_codes)
    
    return check_pc_dict(p_codes)


def get_data_oib(oib_list):
    user_data = None
    company_data = None
    
    for oib in oib_list:
        if not company_data:
            company_data = db.get_company(oib)       
        elif not user_data:
            user_data = get_cur_alias(oib)
            
        if user_data and company_data:
            break
            
    return (user_data, company_data)

def get_cur_alias(oib):
    user = current.user
    if not user['alias_list']: return None

    for alias in user['alias_list']:
        if alias['oib'] == oib: return alias

# TEST
def test_update_iban(test_company):
    update_company_iban('HR012345678519', test_company)
    
def test_check_iban(test_company):
    test_iban = ['HR012345678512', 'HR012322678912', 'HR123456789012']
    print("IBAN:", check_iban(test_iban, test_company))   

def test_check_postal_code():
    p_codes = [10110, 51304]
    print(check_postal_code(p_codes))

def test_get_data_oib():
    oib_list = ['81793146560', '07125893001']
    
    res = get_data_oib(oib_list)
    print(res)

if __name__ == "__main__":
    db.connect_to_db()
    current.user = {
        "_id" : "5ef3105d512a224fb6bc77b7",
        "name" : "aaa",
        "surname" : "bbb",
        "email" : "e@mail.com",
        "password" : { "$binary" : "JDJiJDA4JFVLTmRTeVYwV1phYzA3NkV0M1FOZE93RkdtbkVOQmM0b1NmSjdGTVMxQ0IvR0k3N08yWXpD", "$type" : "00" },
        "personal_archive_id" : "5ef3105e512a224fb6bc77ba",
        "archive_ids" : [ 
            "5ef3105e512a224fb6bc77ba"
        ],
        "alias_list" : [ 
            {
                "ime" : "John",
                "prezime" : "Smith",
                "oib" : "07125893001",
                "iban" : "HR123456789012",
                "postal_code" : "10000"
            }
        ],
        "email_list" : []
    }
    
    #test_company = db.get_company(db.connect_to_db(), '16962783514')
    
    #test_update_iban(test_company)
    #test_check_iban(test_company)
    
    #test_check_postal_code()
    
    test_get_data_oib()