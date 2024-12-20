from flask import Flask, jsonify, request
from datetime import datetime
from simple_salesforce import Salesforce, SFType
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

app = Flask(__name__)

# 示例数据，实际应用中应从数据库或其他持久化存储中获取
custom_objects_data = [
    {"object_Name": "Case__c", "LastModifiedDate": "2020-12-18T15:30:00"},
    {"object_Name": "Account__c", "LastModifiedDate": "2020-12-19T10:45:00"},
    {"object_Name": "Test__c", "LastModifiedDate": "2024-12-19T10:45:00"}
]

def login_to_salesforce(token):
    try:
        # 使用提供的token作为OAuth Token来登录到Salesforce
        sf = Salesforce(instance_url='https:/login.salesforce.com', session_id=token)
        return sf
    except SalesforceAuthenticationFailed as e:
        print(f"Salesforce Authentication Failed: {e}")
        return None

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_custom_object_info():
    token = request.args.get('token')
    
    # 尝试使用token登录Salesforce
    sf = login_to_salesforce(token)
    if not sf:
        return jsonify({"error": "Invalid or missing token"}), 401
    
    custom_objects = []
    for obj in custom_objects_data:
        custom_objects.append({
            "object_name": obj["object_Name"],  # 注意键名匹配
            "LastModifiedDate": datetime.strptime(obj["LastModifiedDate"], "%Y-%m-%dT%H:%M:%S").isoformat()
        })
    
    return jsonify(custom_objects)

@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message="Hello, world!")

if __name__ == '__main__':
    app.run(debug=True)
