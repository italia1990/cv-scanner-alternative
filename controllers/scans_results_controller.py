from models import scan_results
import json


'''
saves scan results to the db and returns the new  id
'''
def save_scan_results(results_dict, user_id=1):

    scan_results_json = {}

    #convert data to json to be stored as strings in the database
    for key in results_dict:
        scan_results_json[key] = json.dumps(results_dict[key])

    # print('the results to be saved to the db is: ', scan_results_json)

    sr = scan_results(user_id=user_id, hard_skills=scan_results_json['hard_skills'], soft_skills=scan_results_json['soft_skills'],
                      best_practices=scan_results_json['best_practices'], sales_index=scan_results_json['sales_index'], similarity_check=scan_results_json['similarity_check'])
    new_scan = sr.save()

    return new_scan.id




'''
get scan results by scan id, returns the stringified data back to a regular json
'''
def get_scan_by_id(scan_id, user_id):
    try:
        sr = scan_results.query.filter_by(id=scan_id, user_id=user_id).first()
        if sr is None:
            return None
            
        return {'similarity_check': json.loads(sr.similarity_check), 'sales_index': json.loads(sr.sales_index), 'best_practices': json.loads(sr.best_practices), 'soft_skills': json.loads(sr.soft_skills), 'hard_skills': json.loads(sr.hard_skills)}

    except Exception as e:
        print('something happened in get_scan_by_id', e)
        return False

'''
get a results set by scan id, returns the stringified data back to a regular json
'''
def get_results_set_by_id(scan_id, user_id, results_set):
    try:
        results_set_data = scan_results.query.with_entities(getattr(scan_results, results_set)).filter_by(id=scan_id, user_id=user_id).first()
        if results_set_data is None:
            return None

        # print(results_set_data)
        return  results_set_data[0]

    except Exception as e:
        print('something happened in get_best_practices_by_id', e)
        return False


