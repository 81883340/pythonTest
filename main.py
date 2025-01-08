from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from simple_salesforce import Salesforce

app = Flask(__name__)

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_sf_objects():
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({'error': 'access_token is missing'}), 400

    # Salesforce instance URL
    instance_url = 'https://ibm176-dev-ed.develop.my.salesforce.com'  # Replace with actual instance URL

    # Initialize Salesforce connection
    sf = Salesforce(instance_url=instance_url, session_id=access_token)

    # Step 1: Get list of all custom objects
    objects = sf.describe()['sobjects']
    custom_objects = [obj['name'] for obj in objects if obj.get('custom')]

    # Step 2: Set cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    inactive_objects = []
    for obj_name in custom_objects:
        try:
            # Step 3: Query each custom object
            query = f"SELECT Id FROM {obj_name} WHERE LastModifiedDate >= '{cutoff_date_str}' LIMIT 1"
            records = sf.query(query)['records']
            inactive_objects.append(obj_name)
            # if not records:
                # inactive_objects.append(obj_name)
        except Exception as e:
            # Handle exceptions for objects that cause errors
            print(f"Error querying {obj_name}: {e}")
            continue

    # Step 4: Return the list of inactive custom objects
    return jsonify(inactive_objects)

if __name__ == '__main__':
    app.run(debug=True)
