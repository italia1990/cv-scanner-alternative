import io
import json
from flask import Flask, jsonify, request, send_file, abort, render_template
# from werkzeug.wrappers import cors
from werkzeug.datastructures import FileStorage

from resume_scanner import ResumeScanner
from models import setup_db
from controllers import scans_results_controller, authController
from controllers.s3_controller import S3Bucket
from functools import wraps
import threading
from flask_cors import CORS
import sys

app = Flask(__name__)
CORS(app)
app.config.from_object('config')
setup_db(app)

'''
wrapper function, it verifies the api key token
'''


def validated_token(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        # if api-key wasn't provided return

        if request.headers.get('api-key', None) is None:
            return jsonify({'success': False, 'message': 'a valid token is missing'}), 401

        token_status = authController.verify_token(request.headers['api-key'])
        token_status = True
        if not token_status:
            return jsonify({'success': False, 'message': 'token is invalid'}), 401

        return f(*args, **kwargs)

    return decorator

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/test', methods=['GET', 'POST'])
def test():
    return render_template('test.html')


'''
calls the resume scanner, stores the data in the db, upload the cv and jd files to s3, return jsonified scan data

'''


@app.route('/resume/scan', methods=['GET', 'POST'])
def scan_resume():
    try:

        data = request.form
        # print('data ===>', data);
        if data.get('user_id', None) is None:
            return {"success": False, "msg": "Required file(s)(user_id) missing, try again."}, 400
        if data.get('job_title', None) is None:
            return {"success": False, "msg": "Required file(s)(jt) missing, try again."}, 400
        if data.get('industry_title', None) is None:
            return {"success": False, "msg": "Required file(s)(it) missing, try again."}, 400
        # if request.files.get('cv', None) is None:
        #     return {"success": False, "msg": "Required file(s)(cv) missing, try again."}, 400
        # if request.files.get('jd', None) is None:
        #     return {"success": False, "msg": "Required file(s)(jd) missing, try again."}, 400
        if data.get('cv', None) is None:
            return {"success": False, "msg": "Required file(s)(cv) missing, try again."}, 400
        if data.get('jd', None) is None:
            return {"success": False, "msg": "Required file(s)(jd) missing, try again."}, 400

        # Get the file extension
        if "@:@" not in data['cv']:
            extension = 'txt'
        else :
            extension = data['cv'].split("@:@")[-1]

        # Create a BytesIO object to mimic a file-like object
        file_like_cv = io.BytesIO(data['cv'].encode())
        file_like_jd = io.BytesIO(data['jd'].encode())

        # Create a FileStorage object
        cv = FileStorage(file_like_cv, filename='cv.txt', content_type='text/plain')
        jd = FileStorage(file_like_jd, filename='jd.txt', content_type='text/plain')
        # setting it 1 because im currently in debugging mode, always set it to provided id when connected to WP
        user_id = data['user_id'] 

        # converting filestorage object to bytes, makes it possible to pass it to the resumescanner func and move the
        # handler back to the start after its done.
        # cv = request.files['cv']
        # if cv.filename.split('.')[-1] not in app.config['ALLOWED_FILES_TYPES']:
        #     return {"success": False, "msg": "Resume file type not allowed, try again."}, 400
        cv_binary = io.BytesIO(cv.read())  # for the s3 upload thread

        # jd = request.files['jd']
        # if jd.filename.split('.')[-1] not in app.config['ALLOWED_FILES_TYPES']:
        #     return {"success": False, "msg": "Job desc file type not allowed, try again."}, 400
        jd_binary = io.BytesIO(jd.read())  # for the s3 upload thread

        print('starting scan')
        resume_scanner_results = ResumeScanner(
            resume_file=cv, resume_extension = extension, jd_file=jd, domain=data['job_title'], industry=data['industry_title'],
            affinda_token='aff_c4db34c8d585992ad719f4255ed7af70f925c497', temp_folder=app.config['TEMP_FOLDER']).start_scan()

        if not resume_scanner_results["success"]:
            return jsonify({"success": False, "msg": resume_scanner_results['msg']}), 400

        resume_scanner_results = resume_scanner_results['results']
        
        """
        to allow none registered users to scan,a user_id of 0 can be sent if it's not a logged in user doing the
        scan, if the scan request is made by a user that isn't logged in it will not be storing neither his results
        or files in the dB or aws s3, just returns the results data.
        """
        scan_id = 0
        if int(len(user_id)) > 0:
            try:
                print('saving scan results to db')
                scan_id = scans_results_controller.save_scan_results(
                    results_dict=resume_scanner_results, user_id=user_id)
                # resume_scanner_results['scan_id'] = scan_id

                # making this a thread of its own can save ~0.5 second
                thread = threading.Thread(target=move_files_to_s3_thread, args=(
                    user_id, scan_id, cv_binary, cv.filename, jd_binary, jd.filename))
                thread.daemon = False
                thread.start()

            except Exception as e:
                print(
                    'something happened while saving to database or connecting to aws s3 ', e)
                pass
        print("Resume Scan Result ", resume_scanner_results)
        return jsonify({"success": True, "scan_id": scan_id, 'results': resume_scanner_results}), 200

    except Exception as e:
        print('an error happened in scan_resume()', e)
        return jsonify({"success": False, "message": e}), 401


# making this a thread of its own can save ~0.5 second
def move_files_to_s3_thread(user_id, scan_id, cv_binary, cv_filename, jd_binary, jd_filename):
    print('in bucket upload thread')
    bucket = S3Bucket(user_id=user_id, scan_id=scan_id)
    # move cv and jd to s3
    bucket.upload_file(file=cv_binary, is_resume=True, filename=cv_filename)
    bucket.upload_file(file=jd_binary, is_resume=False, filename=jd_filename)


'''
returns scan results from the database, returns json
'''


@app.route('/resume/scan/<int:user_id>/<int:scan_id>', methods=['GET'])
def get_scan_results(user_id, scan_id):
    try:
        if user_id <= 0 or scan_id <= 0:
            print('cant get a scan 0 or/for a user 0')
            return jsonify({'success': False, 'msg': 'please sign in first.'}), 400

        scan_res = scans_results_controller.get_scan_by_id(scan_id, user_id)
        if scan_res is None or scan_res == False:
            return jsonify({'success': False, 'msg': 'not found'}), 404

        return jsonify({'success': True, 'results': scan_res}), 200

    except Exception as e:
        print('error in get_scan_results', e)
        return jsonify({'success': False, 'msg': 'please try again.'}), 500


'''
returns scan results set from the database, returns json containing just the results of the selection
'''


@app.route('/resume/scan/<results_set>/<int:user_id>/<int:scan_id>', methods=['GET'])
def get_scan_results_set(results_set, user_id, scan_id):
    if user_id is None or user_id == 0:
        return jsonify({'success': False, 'message': "user not logged in."}), 400

    if results_set is None:
        return jsonify({'success': False, 'message': 'results set name missing.'}), 400

    results_set = results_set.lower().replace('-', '_')
    if results_set not in ['best_practices', 'similarity_check', 'hard_skills', 'soft_skills']:
        return jsonify({'success': False, 'message': results_set + ' does not match an existing results set'})

    scan_res = scans_results_controller.get_results_set_by_id(
        scan_id, user_id, results_set)
    if scan_res is None or scan_res == False:
        abort(404)

    return jsonify({'success': True, 'results': json.loads(scan_res)}), 200


'''
download user cv or jd from S3 storage, takes scanid and userid as url parameters 
'''


@app.route('/resume/scan/<filetype>')
def get_user_cv_or_jd(filetype):
    print(filetype)
    if filetype != 'cv' and filetype != 'jd':
        return jsonify({"success": False, "message": "either request a cv file or a job description file"}), 500
    args = request.args
    if args.get('scanid', None) is None or args.get('userid', None) is None:
        return jsonify({"success": False, "message": "missing arguments scanid, userid"}), 500

    bucket = S3Bucket(user_id=args['userid'], scan_id=args['scanid'])
    # returns a tuple (file binary, file name)
    cv_file_binary = bucket.get_file(
        is_resume=True if filetype == 'cv' else False)

    if cv_file_binary is False:
        return jsonify({"success": False, "message": "something happened while fetching the file from aws, it can be "
                                                     "unavailable"}), 500

    # TODO plan what to do with the file data now
    return send_file(cv_file_binary[0], attachment_filename=cv_file_binary[1])


if __name__ == "__main__":
    # app.run(debug=True)
    # CORS(app.run(debug=False))
    CORS(app.run(host='0.0.0.0', port=8000))
