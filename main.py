from flask import Flask, jsonify, request

app = Flask(__name__)

# 简单的数据存储，实际应用中这应该是数据库。
tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

# 获取所有任务
@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_tasks():
    return jsonify({'tasks': tasks})

# 获取单个任务
@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'task': task[0]})

# 创建新任务
@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        return jsonify({'error': 'Bad request'}), 400
    task = {
        'id': tasks[-1]['id'] + 1 if len(tasks) > 0 else 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201

if __name__ == '__main__':
    app.run(debug=True)
