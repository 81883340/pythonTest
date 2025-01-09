from flask import Flask, request, jsonify
from simple_salesforce import Salesforce

app = Flask(__name__)

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_sf_objects():
    # Step 1: Get access_token and instance_url from query parameters
    access_token = request.args.get('access_token')
    instance_url = request.args.get('instance_url')

    # Step 2: Validate required parameters
    if not access_token or not instance_url:
        return jsonify({
            'error': 'Both access_token and instance_url are required'
        }), 400

    try:
        # Step 3: Initialize Salesforce connection
        sf = Salesforce(instance_url=instance_url, session_id=access_token)

        # Step 4: Get list of all custom objects
        objects = sf.describe()['sobjects']
        custom_objects = [
            obj['name'] for obj in objects
            if obj.get('custom') and obj.get('name').endswith('__c')
        ]

        # Step 5: Check for inactive custom objects
        inactive_objects = []
        for obj_name in custom_objects:
            try:
                # Query each custom object using LAST_N_DAYS:90
                query = f"SELECT Id FROM {obj_name} WHERE LastModifiedDate >= LAST_N_DAYS:90 LIMIT 1"
                records = sf.query(query)['records']
                if not records:
                    inactive_objects.append(obj_name)
            except Exception as e:
                print(f"Error querying {obj_name}: {e}")
                continue

        # Step 6: Return the list of inactive custom objects
        return jsonify({'inactive_objects': inactive_objects})

    except Exception as e:
        # Handle Salesforce connection or other errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
