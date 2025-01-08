from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

@app.route('/sf_objects', methods=['GET'])
def get_sf_objects():
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({'error': 'access_token is missing'}), 400

    # Salesforce instance URL (you may need to retrieve this from OAuth response)
    instance_url = 'https://your-domain.my.salesforce.com'  # Replace with actual instance URL

    # Step 1: Get list of all custom objects
    metadata_url = f"{instance_url}/services/data/v53.0/sobjects/"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(metadata_url, headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to retrieve objects from Salesforce'}), 500
    objects = response.json()['sobjects']

    custom_objects = [obj for obj in objects if obj['custom'] and obj['name'].endswith('__c')]

    # Step 2: Query each custom object for records updated or created in last 90 days
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    inactive_objects = []
    for obj in custom_objects:
        object_name = obj['name']
        query = f"SELECT Id FROM {object_name} WHERE CreatedDate >= '{cutoff_date_str}' OR LastModifiedDate >= '{cutoff_date_str}' LIMIT 1"
        query_url = f"{instance_url}/services/data/v53.0/query/"
        query_response = requests.get(query_url, headers=headers, params={'q': query})
        if query_response.status_code != 200:
            # Handle query error, e.g., insufficient permissions
            continue
        records = query_response.json().get('records', [])
        if not records:
            inactive_objects.append(object_name)

    # Step 3: Return the list of inactive custom objects
    return jsonify(inactive_objects)

if __name__ == '__main__':
    app.run(debug=True)
