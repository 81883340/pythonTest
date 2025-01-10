from flask import Flask, request, jsonify
from simple_salesforce import Salesforce
from Crypto.Cipher import AES
import base64
import logging 

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
    # Step 1: Get encrypted access_token from the header and instance_url from query parameters
    encrypted_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')

    # Step 2: Validate required parameters
    if not encrypted_token or not instance_url:
        return jsonify({'error': 'Both Authorization header and instance_url are required'}), 400

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
    Delete one or more custom objects in the target Salesforce org.
    """
    logging.debug("Received request to delete custom objects")

    # Step 1: Get encrypted access_token and instance_url from query parameters
    encrypted_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')

    # Step 2: Validate required parameters
    if not encrypted_token or not instance_url:
        logging.error("Missing access_token or instance_url")
        return jsonify({'error': 'Both access_token and instance_url are required'}), 400

    # Step 3: Get the list of object names to delete from the request body
    data = request.get_json()
    if not data or 'object_names' not in data:
        logging.error("Missing object_names in request body")
        return jsonify({'error': 'object_names is required in the request body'}), 400

    object_names = data['object_names']
    if not isinstance(object_names, list):
        logging.error("object_names must be a list")
        return jsonify({'error': 'object_names must be a list'}), 400

    try:
        # Step 4: Decrypt the access_token
        access_token = decrypt_token(encrypted_token)
        logging.debug("Access token decrypted successfully")
    except Exception as e:
        logging.error(f"Failed to decrypt access token: {str(e)}")
        return jsonify({'error': 'Invalid token: ' + str(e)}), 401

    try:
        # Step 5: Initialize Salesforce connection
        sf = initialize_salesforce_connection(access_token, instance_url)
        logging.debug("Salesforce connection initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Salesforce connection: {str(e)}")
        return jsonify({'error': str(e)}), 500

    # Step 6: Get all custom objects
    try:
        objects = sf.describe()['sobjects']
        custom_objects = [
            obj['name'] for obj in objects
            if obj.get('custom') and obj.get('name').endswith('__c')
        ]
        logging.debug(f"Available custom objects: {custom_objects}")
    except Exception as e:
        logging.error(f"Failed to fetch custom objects: {str(e)}")
        return jsonify({'error': str(e)}), 500

    # Step 7: Use Metadata API to delete each custom object
    results = []
    metadata = sf.mdapi  # Access Metadata API

    for object_name in object_names:
        try:
            logging.debug(f"Attempting to delete object: {object_name}")

            # Check if the object exists
            if object_name not in custom_objects:
                logging.error(f"Object {object_name} does not exist")
                results.append({"object_name": object_name, "status": "failed", "error": "Object does not exist"})
                continue

            # Attempt to delete the custom object
            delete_result = metadata.CustomObject.delete(object_name)

            # If delete_result is None, assume the operation was successful
            if delete_result is None:
                logging.debug(f"Delete operation returned None for object: {object_name}. Assuming success.")
                results.append({"object_name": object_name, "status": "success"})
            else:
                # Check if the deletion was successful
                if isinstance(delete_result, list) and len(delete_result) > 0 and delete_result[0]['success']:
                    logging.debug(f"Successfully deleted object: {object_name}")
                    results.append({"object_name": object_name, "status": "success"})
                else:
                    error_message = delete_result[0].get("errors", "Unknown error") if isinstance(delete_result, list) else "Invalid response format"
                    logging.error(f"Failed to delete object {object_name}: {error_message}")
                    results.append({"object_name": object_name, "status": "failed", "error": error_message})
        except Exception as e:
            logging.error(f"Error deleting object {object_name}: {str(e)}")
            results.append({"object_name": object_name, "status": "failed", "error": str(e)})

    # Step 8: Return the results of the delete operations
    return jsonify({'results': results})
if __name__ == '__main__':
    # Start the Flask service
    app.run(debug=True)
