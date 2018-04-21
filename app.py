from flask import Flask, request, abort
import requests
from bs4 import BeautifulSoup

vieshow_url = 'https://www.vscinemas.com.tw/'
hot_url = 'https://www.vscinemas.com.tw/film/hot.aspx'
index_url = 'https://www.vscinemas.com.tw/film/index.aspx'
coming_url = 'https://www.vscinemas.com.tw/film/coming.aspx'
movie_dict = {}

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)
############
def crawl_index_movie():
    r = requests.get(index_url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    moviePage = soup.find(class_='pagebar').find_all('a', href=True)

    for p in moviePage[1:]:
        movieList = soup.find(class_='movieList').find_all('li')
        for m in movieList:
            movie_name = "%s (%s)" % (m.find('h2').text, m.find('h3').text)
            movie_info_url = m.find('h2').find('a')['href']
            movie_start_time = m.find('time').text
            movie_img = m.find('img')['src'].replace('../', vieshow_url)
            print(movie_img)
            hot_movie = False
            info = [movie_name, movie_start_time, movie_info_url, hot_movie, []]
            movie_dict[movie_name] = info
        next_page_url = index_url + p['href']
        soup = BeautifulSoup(requests.get(next_page_url).text, 'html.parser')

def search_movie_name(text):
    for movie in movie_dict:
        print(movie)
        if text in movie:
            print("!!!!")
            return movie
    return None

def search_movie_picture(movie_name):
    movie_url = 'https://www.vscinemas.com.tw/film/' + movie_dict[movie_name][2]
    print(movie_url)
    r = requests.get(movie_url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')


############
app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi('bQu1j0/rJMgNGK++uQcD1Pu8zLcB/Gdp3kwwcwrP4Quj33AGyX1wZtTjPmy8TaNTiEgTgbgzGvN7ZMNtBnDPSubZ0waBtV1tLnbRM7x7O0gkO/z165gjVEJ7YvxoBEMLyzjobckPsfnw5Ncb6hH1fQdB04t89/1O/w1cDnyilFU=')
# Channel Secret
handler = WebhookHandler('756c8ca2e53d032ae70d8e1cb6624294')

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    response = search_movie_name(event.message.text);
    #movie_pic = search_movie_picture(response)
    message = TextSendMessage(text=response)
    #message_pic = ImageSendMessage(
    #    original_content_url=message_pic,
    #    preview_image_url=message_pic)
    #line_bot_api.reply_message(event.reply_token, message)
    #line_bot_api.reply_message(event.reply_token, [message,message_pic, message_vid])
    #line_bot_api.reply_message(event.reply_token,"hahahahahaha")print("start chatting!")
    #response = chatbot.get_response(event.meessage.text)
    #message = TextSendMessage(text=response)
    line_bot_api.reply_message(event.reply_token, [message, message_pic])
    #print(response)


import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    crawl_index_movie()
