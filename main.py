from flask import Flask, jsonify, request
from datetime import datetime

# 初始化 Flask 应用
app = Flask(__name__)

# 示例数据，实际应用中应从数据库或其他持久化存储中获取
custom_objects_data = [
    {"object_Name": "Case__c", "LastModifiedDate": "2020-12-18T15:30:00"},
    {"object_Name": "Account__c", "LastModifiedDate": "2020-12-19T10:45:00"},
    {"object_Name": "Test__c", "LastModifiedDate": "2024-12-19T10:45:00"}
]

# 验证 token 的示例函数（请替换为实际的验证逻辑）
def validate_token(token):
    # 这里只是一个简单的示例，实际应该根据你的需求实现
    return token == "your_secret_token"

@app.route('/api/getCustomObjectInfo', methods=['GET'])
def get_custom_object_info():
    token = request.args.get('token')
    
    if not token or not validate_token(token):
        return jsonify({"error": "Invalid or missing token"}), 401
    
    # 获取自定义对象信息，这里使用示例数据
    custom_objects = []
    for obj in custom_objects_data:
        custom_objects.append({
            "object_name": obj["object_name"],
            "last_updated": datetime.strptime(obj["last_updated"], "%Y-%m-%dT%H:%M:%S").isoformat()
        })
    
    return jsonify(custom_objects)

# 定义路由和处理函数
@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message="Hello, world!")

# 如果作为主模块运行，则启动应用
if __name__ == '__main__':
    app.run(debug=True)
