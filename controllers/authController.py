from cryptography.fernet import Fernet

'''
generate an auth token from a text. commented out now, can be used later to dynamically generate new tokens, or just to generate a new token
'''
# def get_encrypted():  
#     try:
#         clear_text = "i am WP cvjury"
#         private_key = '73vhL6fTAJvUBqSx1OAhZJoCrKLilHvyfQ6_FHIjPkc='
#         encrypted_text = Fernet(private_key).encrypt(str(clear_text).encode()).decode()

#         print("original string: ", clear_text)
#         print("encrypted string: ", encrypted_text)

#         return encrypted_text

#     except Exception as e:
#         print('something happened in get_encrypted', e)


'''
decrypt the auth token to clear text, using our private key
verifies that the auth token is correct.
'''


def verify_token(auth_token):
    try:
        # private_key = '73vhL6fTAJvUBqSx1OAhZJoCrKLilHvyfQ6_FHIjPkc='

        # clear_text = Fernet(private_key).decrypt(auth_token.encode()).decode()

        # print('decrypted token ', clear_text)

        # return True if clear_text == "i am WP cvjury" else False
        # NOTE just making this as straight forward, for now.
        return True if auth_token == 'gAAAAABhca1Y-15zmTl0loIZfZTV4vCvtGs_SX17vNv30mqPlrrIU2cPIe4ie6Ke6EXsOdbNKnRtzWEzxrn7RZTKBakbAbmkdQ==' else False
    except Exception as e:
        print('error in verify_token ', e)
        return False
