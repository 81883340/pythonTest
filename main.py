from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64

app = Flask(__name__)

# 确保密钥是32字节
ENCRYPTION_KEY = b'3MVG9aNlkJwuH9vPePXJ1vP3a1vEBPqE'

def decrypt_token(encrypted_token):
    try:
        encrypted_data = base64.b64decode(encrypted_token)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        decrypted_data = unpad(decrypted_padded, AES.block_size).decode('utf-8')
        return decrypted_data
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")

def initialize_salesforce_connection(access_token, instance_url):
    try:
        from simple_salesforce import Salesforce
        return Salesforce(instance_url=instance_url, session_id=access_token)
    except Exception as e:
        raise ValueError(f"Failed to initialize Salesforce connection: {str(e)}")

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_sf_objects():
    encrypted_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')
    
    if not encrypted_token or not instance_url:
        return jsonify({'error': 'Both access_token and instance_url are required'}), 400
    
    try:
        access_token = decrypt_token(encrypted_token)
    except Exception as e:
        return jsonify({'error': 'Invalid token: ' + str(e)}), 401
    
    try:
        sf = initialize_salesforce_connection(access_token, instance_url)
        describe_result = sf.describe()
        if 'sobjects' not in describe_result:
            return jsonify({'error': 'Failed to retrieve Salesforce objects'}), 500
        
        objects = describe_result['sobjects']
        custom_objects = [obj['name'] for obj in objects if obj.get('custom') and obj.get('name').endswith('__c')]
        
        inactive_objects = []
        for obj_name in custom_objects:
            query = f"SELECT Id FROM {obj_name} WHERE LastModifiedDate >= LAST_N_DAYS:90 LIMIT 1"
            try:
                query_result = sf.query(query)
                if not query_result['records']:
                    inactive_objects.append(obj_name)
            except Exception as e:
                print(f"Error querying {obj_name}: {e}")
                continue
        
        return jsonify({'inactive_objects': inactive_objects})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
