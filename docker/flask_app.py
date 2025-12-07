# app.py
from flask import Flask

app = Flask(__name__)

@app.route('/flask')
def hello_world():
    return 'Hello from the Python Flask Webserver on port 8868!'

if __name__ == '__main__':
    # Flask will run on the specified port
    app.run(host='0.0.0.0', port=8868)