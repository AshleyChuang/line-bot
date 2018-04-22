from flask import Flask, request, abort
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

vieshow_url = 'https://www.vscinemas.com.tw/'
hot_url = 'https://www.vscinemas.com.tw/film/hot.aspx'
index_url = 'https://www.vscinemas.com.tw/film/index.aspx'
detail_url_by_id = 'https://www.vscinemas.com.tw/film/detail.aspx?id='
coming_url = 'https://www.vscinemas.com.tw/film/coming.aspx'
movie_dict = {}
# movie info by movie id: 0->movie name, 1->image, 2->{theater_id:theater_name}, 3->{theater_id: [ dates "[date, [tuple(time, url)] ]" ]}

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
            #movie_name = "%s (%s)" % (m.find('h2').text, m.find('h3').text)
            movie_name = m.find('h2').text
            movie_id = re.search('id=(.*)',m.find('h2').find('a')['href']).group(1)
            movie_info_url = vieshow_url + 'film/' + m.find('h2').find('a')['href']
            movie_start_time = m.find('time').text
            movie_img = m.find('img')['src'].replace('../', vieshow_url)
            #info = [movie_img,movie_start_time, movie_info_url, {}]
            info = [movie_name, movie_img, {}, {}]
            movie_dict[movie_id] = info
        next_page_url = index_url + p['href']
        soup = BeautifulSoup(requests.get(next_page_url).text, 'html.parser')

def search_movie_id(text):
    for movie_id in movie_dict:
        if text in movie_dict[movie_id][0]:
            return movie_id
    return None

def get_trailer_url(url):
    r = requests.get(url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    movieVideo = soup.find(class_='mainVideo')
    if movieVideo is None:
        return None
    return movieVideo.find('iframe')['src']

def crawl_theater(movie_id):
    url = detail_url_by_id + movie_id
    if len(movie_dict[movie_id][2]) != 0:
        return None
    movie_theater = {}
    r = requests.get(url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    theaterList = soup.find("ul", {"class": "versionList"}).find("li").find_all("li")
    for i in theaterList:
        t = i.find('a')
        movie_theater[t['href']] = t.text
    movie_dict[movie_id][2] = movie_theater

def crawl_movie_time(movie_id, movie_theater):
    # movie_dict_key=3  -> {theater_id: [ dates "[date, [tuple(time, url)] ]" ]}
    all_times_in_theaters = [] # element: [date, [tuple]]
    url = detail_url_by_id + movie_id
    print(movie_id)
    print(movie_theater[1:])
    r = requests.get(url)
    content = r.text
    soup = BeautifulSoup(content, 'html.parser')
    movie_times = soup.find("article", {"id": movie_theater[1:]})
    if movie_times is None:
        return []
    movieDays = movie_times.find_all("div", {"class": "movieDay"})
    dates = [] # date -> times&urls
    for day in movieDays:
        date2times = []
        #dates.append(date)
        date = day.find("h4").text
        date2times.append(date)
        dates.append(date)
        sessions = day.find("ul", {"class": "bookList"}).find_all("li")
        timesessions = []
        for sess in sessions:
            time_session = sess.find('a')
            time = time_session.text
            if "soldout" in sess.attrs['class']:
                continue
            booking_url = time_session['href']
            timesessions.append( (time, booking_url) )
        date2times.append(timesessions)
        all_times_in_theaters.append(date2times)
    movie_dict[movie_id][3][movie_theater] = all_times_in_theaters
    print(all_times_in_theaters)
    return dates

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
    movie_id = search_movie_id(keyword)
    if movie_id is None:
        return TextSendMessage(text="沒有這個電影耶～查查看別的吧！")
    movie_name = movie_dict[movie_id][0]
    movie_pic = movie_dict[movie_id][1]
    movie_url = detail_url_by_id + movie_id
    movie_trailer = get_trailer_url(movie_url)
    #print(movie_trailer)
    if movie_trailer is None:
        uri_template = URITemplateAction(type = 'uri',label='Picture', uri=movie_pic)
    else:
        uri_template = URITemplateAction(type = 'uri',label='Trailer', uri=movie_trailer)
    buttons_template = ButtonsTemplate(
        type='buttons', title=movie_name[0:40],
        text='Check out more information for the movie!',
        thumbnail_image_url = movie_pic,
        actions=[PostbackTemplateAction(label='Movie Time', data='movie=%s&action=1&'%movie_id),uri_template]
        )
    message = TemplateSendMessage(
        type = 'template', alt_text=movie_name,
        template=buttons_template
        )
    return message

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = get_movie_by_keyword(event.message.text)
    line_bot_api.reply_message(event.reply_token, message)

def generate_carousel_col(date_times, movie_id, movie_theater):
    date = date_times[0]
    times = date_times[1]
    if len(times) <= 10:
        col = CarouselColumn(
                title=date,
                actions=[
                    PostbackTemplateAction(
                        type='postback',label='Select Movie Time',
                        data='movie=%s&action=4&theater=%s&date=%s&slot=0&' %(movie_id, movie_theater, movie_date)
                    )
                ]
            )
        return col
    else:
        col = CarouselColumn(
                title=date,
                actions=[
                    PostbackTemplateAction(
                        type='postback',label='上午時段',
                        data='movie=%s&action=4&theater=%s&date=%s&slot=1&' %(movie_id, movie_theater, movie_date)
                    ),
                    PostbackTemplateAction(
                        type='postback',label='下午時段',
                        data='movie=%s&action=4&theater=%s&date=%s&slot=2&' %(movie_id, movie_theater, movie_date)
                    ),
                    PostbackTemplateAction(
                        type='postback',label='晚間時段',
                        data='movie=%s&action=4&theater=%s&date=%s&slot=3&' %(movie_id, movie_theater, movie_date)
                    )
                ]
            )
        return col

@handler.add(PostbackEvent)
def handle_message(event):
    movie_id = re.search('movie=(.+?)&',event.postback.data).group(1)
    action_type = re.search('&action=(.+?)&',event.postback.data).group(1)
    movie_name = movie_dict[movie_id][0]
    ## action: 1->電影院 , 2->只有一個電影院 (confirm-> 1:yes, 0:no), 4->
    #if action_type == '1':
    if action_type == '1':
        crawl_theater(movie_id)
        theaters = movie_dict[movie_id][2]
        if len(theaters) == 1:
            # confirm template
            theater = next(iter(theaters))
            text = '《%s》目前只有在這個影城播出喔！\n想要查詢更詳細的時刻表嗎？' %(movie_name)
            confirm_template = ConfirmTemplate(
                type = 'confirm', text= theaters[theater],
                actions=[
                    PostbackTemplateAction(
                        type = 'postback',
                        label='Yes', display_text='Yes',
                        data='movie=%s&action=2&confirm=1&theater=%s&' %(movie_id, theater)
                    ),
                    PostbackTemplateAction(
                        type = 'postback',
                        label='No', display_text='No. I want to check out other movies.',
                        data='movie=%s&action=2&confirm=0&' %(movie_id)
                    )
                ]
            )
            message = TemplateSendMessage(
                type='template',
                alt_text='Confirmation',
                template=confirm_template
            )
            line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=text),message])
        else:
            text = ['《',movie_name,'》在這些影城都有喔～想要在哪一個影城看呀？\n']
            for i in theaters:
                text.append('・'+theaters[i]+'\n')
            text = ''.join(text)
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=text))
    elif action_type == '2':
        confirm_type = re.search('&confirm=(.+?)&',event.postback.data).group(1)
        print(event.postback.data)
        if confirm_type == '1':
            # 用carousel來分上午下午晚上
            movie_theater = re.search('&theater=(.+?)&',event.postback.data).group(1)
            crawl_movie_time(movie_id, movie_theater)
            movie_days = movie_dict[movie_id][3][movie_theater] # [date_times,...]
            if len(movie_days) <= 0:
                line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text="Sorry! Can't find any movie times in the theater. Try another movie!"),
                TextSendMessage(text='Search for other movies by keyword!')])
            else:
                movie_days_col = []
                description = ''.join(['《',movie_name, '》@', movie_dict[movie_id][2][movie_theater]])
                for date_times in movie_days:
                    col = generate_carousel_col(date_times, movie_id, movie_theater)
                    movie_days_col.append(col)
                carousel_template = CarouselTemplate(tyep='carousel', columns=movie_days_col)
                carousel_template_message = TemplateSendMessage(type = 'template',alt_text='Moive Dates',template=carousel_template)
                line_bot_api.reply_message(event.reply_token, [TextSendMessage(text=description),carousel_template_message])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='Search for other movies by keyword!'))
    elif action_type =='4':
        movie_theater = re.search('&theater=(.+?)&',event.postback.data).group(1)
        movie_date = re.search('&date=(.+?)&',event.postback.data).group(1)
        time_slot = re.search('&slot=(.+?)&',event.postback.data).group(1)
        if time_slot == '0':
            # display all the times
            print(movie_dict[movie_id][3][movie_theater])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='test'))
        elif time_slot == '1':
            # only in morning
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='test1'))
        elif time_slot == '2':
            # only in afternoon
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='test2'))
        elif time_slot == '3':
            # only in night
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='test3'))

crawl_index_movie()

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    #crawl_index_movie()
    app.run(host='0.0.0.0', port=port)
