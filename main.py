import logging
from flask import Flask, request, jsonify
from simple_salesforce import Salesforce
import asyncio
import aiohttp

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def query_salesforce_object(session, instance_url, access_token, obj_name):
    """
    Asynchronously query a Salesforce object to check for recent modifications.
    """
    try:
        query = f"SELECT Id FROM {obj_name} WHERE LastModifiedDate >= LAST_N_DAYS:90 LIMIT 1"
        async with session.get(
            f"{instance_url}/services/data/v57.0/query",
            params={"q": query},
            headers={"Authorization": f"Bearer {access_token}"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return obj_name, bool(data['records'])
            else:
                logger.error(f"Error querying {obj_name}: {response.status} - {await response.text()}")
                return obj_name, False
    except Exception as e:
        logger.error(f"Exception while querying {obj_name}: {e}")
        return obj_name, False

async def get_inactive_objects(instance_url, access_token, custom_objects):
    """
    Asynchronously check for inactive Salesforce custom objects.
    """
    inactive_objects = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            query_salesforce_object(session, instance_url, access_token, obj_name)
            for obj_name in custom_objects
        ]
        results = await asyncio.gather(*tasks)
        for obj_name, is_active in results:
            if not is_active:
                inactive_objects.append(obj_name)
    return inactive_objects

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_sf_objects():
    """
    Flask endpoint to get inactive Salesforce custom objects.
    """
    try:
        # Step 1: Get access_token and instance_url from query parameters
        access_token = request.args.get('access_token')
        instance_url = request.args.get('instance_url')

        # Step 2: Validate required parameters
        if not access_token or not instance_url:
            return jsonify({
                'error': 'Both access_token and instance_url are required'
            }), 400

        # Step 3: Initialize Salesforce connection
        sf = Salesforce(instance_url=instance_url, session_id=access_token)

        # Step 4: Get list of all custom objects
        objects = sf.describe()['sobjects']
        custom_objects = [
            obj['name'] for obj in objects
            if obj.get('custom') and obj.get('name').endswith('__c')
        ]

        # Step 5: Check for inactive custom objects asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        inactive_objects = loop.run_until_complete(
            get_inactive_objects(instance_url, access_token, custom_objects)
        )

        # Step 6: Return the list of inactive custom objects
        return jsonify({'inactive_objects': inactive_objects})

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
