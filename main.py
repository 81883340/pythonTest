from flask import Flask, jsonify

# 初始化 Flask 应用
app = Flask(__name__)

# 定义路由和处理函数
@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message="Hello, world!")

# 如果作为主模块运行，则启动应用
if __name__ == '__main__':
    app.run(debug=True)
