from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/generator/', methods=['POST'])
def generate():
    data = request.json
    
