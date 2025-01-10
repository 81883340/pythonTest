from flask import Flask, request, jsonify
from simple_salesforce import Salesforce
from Crypto.Cipher import AES
import base64

app = Flask(__name__)

# Hardcoded encryption key (must match the key used in Apex)
ENCRYPTION_KEY = b'3MVG9aNlkJwuH9vPePXJ1vP3a1vEBPqE'  # Replace with your actual 32-byte key

def decrypt_token(encrypted_token):
    """
    Decrypt the access_token encrypted by Apex.
    :param encrypted_token: Encrypted token (Base64 encoded)
    :return: Decrypted access_token
    """
    try:
        # Base64 decode
        encrypted_data = base64.b64decode(encrypted_token)
        # Extract IV (first 16 bytes) and the actual encrypted data
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        # Initialize AES decryptor
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
        # Decrypt
        decrypted_data = cipher.decrypt(ciphertext)
        # Remove padding (PKCS7)
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]
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
        access_token = decrypt_token(encrypted_token)
    except Exception as e:
        return jsonify({'error': 'Invalid token: ' + str(e)}), 401

    try:
        # Step 4: Initialize Salesforce connection
        sf = initialize_salesforce_connection(access_token, instance_url)

        # Step 5: Get all custom objects
        objects = sf.describe()['sobjects']
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
                records = sf.query(query)['records']
                if not records:
                    inactive_objects.append(obj_name)
            except Exception as e:
                print(f"Error querying {obj_name}: {e}")
                continue

        # Step 7: Return the list of inactive custom objects
        return jsonify({'inactive_objects': inactive_objects})

    except Exception as e:
        # Handle Salesforce connection or other errors
        return jsonify({'error': str(e)}), 500

@app.route('/api/deleteCustomObject', methods=['POST'])
def delete_custom_object():
    """
    Delete a custom object in the target Salesforce org.
    """
    # Step 1: Get encrypted access_token and instance_url from query parameters
    encrypted_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')

    # Step 2: Validate required parameters
    if not encrypted_token or not instance_url:
        return jsonify({'error': 'Both access_token and instance_url are required'}), 400

    # Step 3: Get the object name to delete from the request body
    data = request.get_json()
    if not data or 'object_name' not in data:
        return jsonify({'error': 'object_name is required in the request body'}), 400

    object_name = data['object_name']

    try:
        # Step 4: Decrypt the access_token
        access_token = decrypt_token(encrypted_token)
    except Exception as e:
        return jsonify({'error': 'Invalid token: ' + str(e)}), 401

    try:
        # Step 5: Initialize Salesforce connection
        sf = initialize_salesforce_connection(access_token, instance_url)

        # Step 6: Use Metadata API to delete the custom object
        metadata = sf.mdapi  # Access Metadata API
        delete_result = metadata.CustomObject.delete(object_name)

        # Step 7: Check the result of the delete operation
        if delete_result[0]['success']:
            return jsonify({'message': f'Custom object {object_name} deleted successfully'})
        else:
            return jsonify({'error': f'Failed to delete custom object {object_name}: {delete_result[0]["errors"]}'}), 500

    except Exception as e:
        # Handle Salesforce connection or other errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the Flask service
    app.run(debug=True)
