from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS
import logging
import sys
from config import HTTP_PORT
from mod_model import *
# from api.config import *

app = Flask(__name__)
CORS(app)

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/', methods=['GET'])
def index():
    return 'hi, look around'

@app.route('/api/question', methods=['POST'])
def post_question():
    # print(request.get_json())
    ct = request.content_type
    if ct != 'application/json':
        return jsonify({'error':'content type must be application/json'}), 400
    json = request.get_json(silent=True)
    question = json.get('question')
    print(question)
    user_id = json.get('user_id')
    logging.info("post question `%s` for user `%s`", question, user_id)

    resp = chat(question, user_id)
    data = {'answer':resp}

    return jsonify(data), 200

if __name__ == '__main__':
    init_llm()
    # uncomment till line 48 to run web crawling if crawled_data is empty

    # start_url = [
    #     'https://docs.mparticle.com/',
    #     'https://docs.lytics.com/',
    #     'https://docs.zeotap.com/home/en-us/',
    #     'https://segment.com/docs/?ref=nav',
    # ]
    # for url in start_url:
    #     crawl_website(url)
    print('Happening...\n\n\n\n')
    index = init_index(Settings.embed_model)
    init_query_engine(index)
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=True)

