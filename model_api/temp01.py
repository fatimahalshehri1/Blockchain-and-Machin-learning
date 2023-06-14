from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import pickle as pk
import json

app = Flask(__name__, template_folder='pages')

model = pk.load(open(r'C:\Users\sun com\Desktop\My project\model_api\Models\RF.pkl', 'rb'))
scl = pk.load(open(r'C:\Users\sun com\Desktop\My project\model_api\Models\StScl.pkl', 'rb'))

#model = pk.load(open(r'C:\Users\coder\Documents\workspaces\python\fatimah\model_api\Models\RF.pkl', 'rb'))
#scl = pk.load(open(r'C:\Users\coder\Documents\workspaces\python\fatimah\model_api\Models\StScl.pkl', 'rb'))


def pred_file(file):
    data = pd.read_csv(file) # type: ignore
    data.drop('Unnamed: 0', axis=1, inplace=True)
    x = data.iloc[0]

    features = scl.transform(np.array([x]))

    features = features.reshape(1, 30969)
    y_pred = model.predict(features)
    return y_pred


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def result():
    file = request.files['file']
    if file:
        y_pred = pred_file(file)
        if y_pred == 1:
            output = '\nIt\'s a Ransomware'
        else:
            output = '\nIt\'s not a Ransomware'
        print(output)
        return render_template("result.html", result=output)

    else:
        error = "No file uploaded."
        return render_template('index.html', error=error)


@app.route('/upload-json', methods=['POST'])
def result_json():
    file = request.files['file']
    if file:
        y_pred = pred_file(file)
        return jsonify({"is_ransomware": "yes" if y_pred[0] == 1 else "no"})

    else:
        error = "No file uploaded."
        return render_template('index.html', error=error)

@app.errorhandler(json.JSONDecodeError)
def handle_json_decode_error(error):
    return render_template('error.html', error='Invalid JSON response')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
