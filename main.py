from flask import Flask, request, jsonify
from simple_salesforce import Salesforce
from Crypto.Cipher import AES
import base64

app = Flask(__name__)

# Hardcoded encryption key (must match the key used in Apex)
ENCRYPTION_KEY = b'3MVG9aNlkJwuH9vPePXJ1vP3a1vEBPqE'  # 32-byte key

def decrypt_token(encrypted_token):
    """
    Decrypt the access_token encrypted by Apex.
    :param encrypted_token: Encrypted token (Base64 encoded)
    :return: Decrypted access_token
    """
    try:
        print(f"Encrypted token (Base64): {encrypted_token}")
        encrypted_data = base64.b64decode(encrypted_token)
        print(f"Encrypted data (bytes): {encrypted_data}")
        iv = encrypted_data[:16]
        print(f"IV (hex): {iv.hex()}")
        ciphertext = encrypted_data[16:]
        print(f"Ciphertext (hex): {ciphertext.hex()}")
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(ciphertext)
        print(f"Decrypted data (with padding): {decrypted_data}")
        padding_length = decrypted_data[-1]
        print(f"Padding length: {padding_length}")
        decrypted_data = decrypted_data[:-padding_length]
        print(f"Decrypted data (without padding): {decrypted_data}")
        return decrypted_data.decode('utf-8')
    except Exception as e:
        raise ValueError("Decryption failed: " + str(e))

def initialize_salesforce_connection(access_token, instance_url):
    """
    Initialize a Salesforce connection using the provided access_token and instance_url.
    :param access_token: Decrypted access_token
    :param instance_url: Salesforce instance URL
    :return: Salesforce connection object
    """
    try:
        return Salesforce(instance_url=instance_url, session_id=access_token)
    except Exception as e:
        raise ValueError(f"Failed to initialize Salesforce connection: {str(e)}")

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_sf_objects():
    """
    Retrieve custom objects in Salesforce that have not been modified in the last 90 days.
    """
    # Step 1: Get encrypted access_token and instance_url from query parameters
    encrypted_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')

    # Step 2: Validate required parameters
    if not encrypted_token or not instance_url:
        return jsonify({'error': 'Both access_token and instance_url are required'}), 400

    try:
        # Step 3: Decrypt the access_token
        # access_token = decrypt_token(encrypted_token)
        access_token = encrypted_token
    except Exception as e:
        return jsonify({'error': 'Invalid token: ' + str(e)}), 401

    try:
        # Step 4: Initialize Salesforce connection
        sf = initialize_salesforce_connection(access_token, instance_url)

        # Step 5: Get all custom objects
        describe_result = sf.describe()
        if 'sobjects' not in describe_result:
            return jsonify({'error': 'Failed to retrieve Salesforce objects'}), 500

        objects = describe_result['sobjects']
        custom_objects = [
            obj['name'] for obj in objects
            if obj.get('custom') and obj.get('name').endswith('__c')
        ]

        # Step 6: Check for inactive custom objects
        inactive_objects = []
        for obj_name in custom_objects:
            try:
                # Query if any records have been modified in the last 90 days
                query = f"SELECT Id FROM {obj_name} WHERE LastModifiedDate >= LAST_N_DAYS:90 LIMIT 1"
                query_result = sf.query(query)
                if not query_result['records']:
                    inactive_objects.append(obj_name)
            except Exception as e:
                print(f"Error querying {obj_name}: {e}")
                continue

        # Step 7: Return the list of inactive custom objects
        return jsonify({'inactive_objects': inactive_objects})

    except Exception as e:
        # Handle Salesforce connection or other errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the Flask service
    app.run(debug=True)
