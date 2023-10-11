import io
import boto3


class S3Bucket():

    def __init__(self, user_id, scan_id):
        self.bucket_name = 'resume-scans'  # hardcoded
        self.region = 'eu-central-1'
        self.user_id = user_id
        self.scan_id = scan_id
        self.s3_client = boto3.client('s3')

    def upload_file(self, file, is_resume, filename):
        try:
            print('uploading file: ', filename)

            if self.check_resumes_scans_bucket_exists():
                file_type = 'cv' if is_resume else 'jd'
                self.s3_client.upload_fileobj(file, self.bucket_name, 'u-' + str(
                    self.user_id) + '/s-' + str(self.scan_id) + '/' + file_type + '/' + filename)

                print('uploaded to s3')
                return True

            return False

        except Exception as e:
            print('something happened while uploading file to aws s3: ', e)
            return False

    def get_file(self, is_resume):
        try:
            file_type = 'cv' if is_resume else 'jd'
            file_prefix = 'u-' + str(self.user_id) + '/s-' + str(self.scan_id) + '/' + file_type + '/'
            # list all the objects, but since each of these directories currently just have 1 file cv or jd,
            # i'm picking the file in index [0]
            file_name = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=file_prefix)['Contents'][0][
                'Key']
            print(file_name)
            if file_name is None:
                return False

            file_bytes = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_name)['Body'].read()

            return io.BytesIO(file_bytes), file_name.split('/')[-1]
        except Exception as e:
            print('something happened in get_file', e)
            return False

    def check_resumes_scans_bucket_exists(self):

        response = self.s3_client.list_buckets()

        # Output the bucket names
        for bucket in response['Buckets']:
            if bucket["Name"] == self.bucket_name:
                print('resume-scans bucket found')
                return True

        print('resume-scans bucket not found, creating it')
        return self.create_resumes_scans_bucket()

    def create_resumes_scans_bucket(self):

        try:
            region = 'eu-central-1'
            self.s3_client = boto3.client('s3', region_name=region)
            self.s3_client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration={
                'LocationConstraint': region})
            return True
        except Exception as e:
            print(e)
            return False
