from flask import Flask, request, abort
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

vieshow_url = 'https://www.vscinemas.com.tw/'
hot_url = 'https://www.vscinemas.com.tw/film/hot.aspx'
index_url = 'https://www.vscinemas.com.tw/film/index.aspx'
coming_url = 'https://www.vscinemas.com.tw/film/coming.aspx'
movie_dict = {} # movie info: 0->image, 1->start time, 2->detail_url, 3->{theaterList: movie time #}

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, PostbackEvent, TextMessage, TextSendMessage,TemplateSendMessage, ButtonsTemplate,
    PostbackTemplateAction, MessageTemplateAction,
    URITemplateAction, DatetimePickerTemplateAction,
    ConfirmTemplate, CarouselTemplate, CarouselColumn,
    ImageCarouselTemplate, ImageCarouselColumn
)
############
def crawl_index_movie():
    r = requests.get(index_url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    moviePage = soup.find(class_='pagebar').find_all('a', href=True)
    movie_dict.clear();
    for p in moviePage[1:]:
        movieList = soup.find(class_='movieList').find_all('li')
        for m in movieList:
            movie_name = "%s (%s)" % (m.find('h2').text, m.find('h3').text)
            movie_info_url = vieshow_url + 'film/' + m.find('h2').find('a')['href']
            movie_start_time = m.find('time').text
            movie_img = m.find('img')['src'].replace('../', vieshow_url)
            info = [movie_img,movie_start_time, movie_info_url, {}]
            movie_dict[movie_name] = info
        next_page_url = index_url + p['href']
        soup = BeautifulSoup(requests.get(next_page_url).text, 'html.parser')

def search_movie_name(text):
    for movie in movie_dict:
        if text in movie:
            return movie
    return None

def get_trailer_url(movie_name):
    url = movie_dict[movie_name][2]
    r = requests.get(url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    movieVideo = soup.find(class_='mainVideo')
    if movieVideo is None:
        return None
    return movieVideo.find('iframe')['src']

def crawl_theater(movie_name):
    url = movie_dict[movie_name][2]
    if len(movie_dict[movie_name][3]) != 0:
        return None
    movie_theater = {}
    r = requests.get(url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    theaterList = soup.find("ul", {"class": "versionList"}).find("li").find_all("li")
    for i in theaterList:
        t = i.find('a')
        movie_theater[t.text] = t['href']
    movie_dict[movie_name][3] = movie_theater
    print(movie_dict[movie_name][3])

############
app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi('bQu1j0/rJMgNGK++uQcD1Pu8zLcB/Gdp3kwwcwrP4Quj33AGyX1wZtTjPmy8TaNTiEgTgbgzGvN7ZMNtBnDPSubZ0waBtV1tLnbRM7x7O0gkO/z165gjVEJ7YvxoBEMLyzjobckPsfnw5Ncb6hH1fQdB04t89/1O/w1cDnyilFU=')
# Channel Secret
handler = WebhookHandler('756c8ca2e53d032ae70d8e1cb6624294')

# push every day
'''
try:
    line_bot_api.push_message('U84434259e4dcdd16ea11fd37a358b6e7', TextSendMessage(text='Hello World!'))
except LineBotApiError as e:
    abort(400)
'''

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    #app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

def get_movie_by_keyword(keyword):
    movie_name = search_movie_name(keyword)
    if movie_name is None:
        return TextSendMessage(text="沒有這個電影耶～查查看別的吧！")
    movie_pic = movie_dict[movie_name][0]
    movie_url = movie_dict[movie_name][2]
    movie_trailer = get_trailer_url(movie_name)
    #print(movie_trailer)
    if movie_trailer is None:
        uri_template = URITemplateAction(type = 'uri',label='Picture', uri=movie_pic)
    else:
        uri_template = URITemplateAction(type = 'uri',label='Trailer', uri=movie_trailer)
    buttons_template = ButtonsTemplate(
        type='buttons', title=movie_name[0:40],
        text='Please select!',
        thumbnail_image_url = movie_pic,
        actions=[PostbackTemplateAction(label='Movie Time', data='movie=%s&action=1'%movie_name),uri_template]
        )
        #URITemplateAction(type = 'uri',label='Check out the trailer', uri=movie_trailer)
        #PostbackTemplateAction(label='Movie Times', data='movie=%s&action=1'%movie_name),
    message = TemplateSendMessage(
        type = 'template', alt_text='Buttons alt text',
        template=buttons_template
        )
    return message

def get_theater(keyword):
    theaters = movie_dict[current_movie][3].keys()
    for i in theaters:
        if keyword in i:
            message = TextSendMessage(text=i)
            return message
    return TextSendMessage(text=next(iter(theaters)))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = get_movie_by_keyword(event.message.text)
    line_bot_api.reply_message(event.reply_token, message)

@handler.add(PostbackEvent)
def handle_message(event):
    movie_name = re.search('movie=(.*)&',event.postback.data).group(1)
    action_type = re.search('&action=(.*)',event.postback.data).group(1)
    movie_url = movie_dict[movie_name][2]
    ## action: 1->場次
    #if action_type == '1':
    crawl_theater(movie_name)
    theaters = movie_dict[movie_name][3]
    if len(theaters) == 1:
        # confirm template
        text = '這場電影只有在這個影城播出喔！\n想要查詢更詳細的時刻表嗎？'
        message = TemplateSendMessage(
            alt_text='Confirm template',
            template=ConfirmTemplate(
                type = 'confirm',
                text= next(iter(theaters)),
                actions=[
                    PostbackTemplateAction(
                        type = 'postback',
                        label='Yes', display_text='Yes',
                        data='action=buy&itemid=1'
                    ),
                    PostbackTemplateAction(
                        type = 'postback',
                        label='No. I want to search for other movies', display_text='No. I want to search for other movies',
                        data='action=buy&itemid=1'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=text))
    else:
        text = ['這個電影在這些影城都有喔～想要在哪一個影城看呀？\n']
        for i in theaters:
            text.append('・'+i+'\n')
        text = ''.join(text)
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=text))

crawl_index_movie()
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    #crawl_index_movie()
    app.run(host='0.0.0.0', port=port)
