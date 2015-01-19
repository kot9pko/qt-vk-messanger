#!/bin/env python2
# -*- coding: utf-8 -*- 
# coding=utf-8

import sys
import signal
import vk
from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import QUrl, QTextCodec
from PyQt4.QtWebKit import QWebView
import urlparse
import requests
import json


# Авторизация с помощью сайта
class WebLogin(QWebView):
    def __init__(self):
        QWebView.__init__(self)
        self.auth_url = 'https://oauth.vk.com/authorize?client_id=4617916&scope=photos,videos,messages,status&display=mobile&v=5.26&response_type=token'
        self.setFixedSize(350, 430)
        self.loadFinished.connect(self._result_available)
        self.urlChanged.connect(self.catchtoken)
        icon = QtGui.QIcon('icon.png')
        self.setWindowIcon(icon)
        self.setWindowTitle("Вход")
        self.access_token = None
        self.load(QUrl(self.auth_url))
        print 'login form created'
        
    def catchtoken(self):
        if 'email=' in str(QUrl.encodedQuery(self.url())):
            self.setFixedSize(350, 500)
        if 'sid=' in str(QUrl.encodedQuery(self.url())):
            self.setFixedSize(350, 540)
        fragment = str(QUrl.encodedFragment(self.url()))
        
        print 'WebLogin. Current URL: ' + str(self.url())
        if QUrl.hasFragment(self.url()):
            if 'error_reason=user_denied' in fragment:
                print 'Окно авторизации: Юзер нажал отмену. Уходим отсюда, нас тут не любят :('
                self.close()
            else:
                self.access_token = urlparse.parse_qs(fragment)['access_token'][0] 
                #print self.access_token                                # Отладочная информация. Полученный токен, который надо отдать в другую форму
                with open('token', 'w') as f:
                    f.write(self.access_token)
                check_token(self.access_token)                          # Костыль. В дальнейшем исправить.
                self.close()
        
        # Если юзер вдруг захочет отвлечься от авторизации, не дадим ему лазить по сайту.
        # К сожалению, это приводит к невозможности регистрации через эту форму
        if QUrl.encodedHost(self.url()) != b'oauth.vk.com':             
            self.load(QUrl(auth_url))
            print('nope')    
    
    def _result_available(self, ok):
        frame = self.page().mainFrame()


# Окно диалогов
class MainForm(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.ui = uic.loadUi("mainform.ui", self)
        self.setWindowTitle('Сообщения')
        self.refresh.triggered.connect(core.fetch_dialogs)
        self.dialogList.itemSelectionChanged.connect(core.get_history)
        self.logout.triggered.connect(core.vklogout)
        self.send.clicked.connect(core.send_message)
        self.pushButton.clicked.connect(core.longpoll_handler)

        
    def setStatus(self):
        print core('status.set', text='тестовый статус')
    
    def set_title(self):
        global profile_info
        try:
            profile_info = core('account.getProfileInfo')
        except requests.adapters.ConnectionError:
            print "Error: No Internet connection"
        else:
            mainf.setWindowTitle(u'Сообщения - ' + profile_info['first_name'] + ' ' + profile_info['last_name'])

        
# Ядро программы
class vkCore(QtCore.QObject, vk.API):
    def __init__(self, api_version='5.26', timeout=5, access_token=None):
        QtCore.QObject.__init__(self)
        
        self.api_version = api_version
        self.access_token = access_token
        self._default_timeout = timeout
        
        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.dialogs_offset = 0         # смещение маркера диалогов слева
        self.lp_info = None
        
        
    def longpoll_get(self):
        self.lp_info = self('messages.getLongPollServer', use_ssl=1)
        print self.lp_info
        self.longpoll_handler()
        
    def longpoll_handler(self):
        bitmask = {
                'UNREAD'        : 0b1,
                'OUTBOX'        : 0b10,
                'REPLIED'       : 0b100,
                'IMPORTANT'     : 0b1000,
                'CHAT'          : 0b10000,
                'FRIENDS'       : 0b100000,
                'SPAM'          : 0b1000000,
                'DELETED'       : 0b10000000,
                'FIXED'         : 0b100000000,
                'MEDIA'         : 0b1000000000
            }
        
        if self.lp_info:
            url = "https://%s?act=a_check&key=%s&ts=%s&wait=1&mode=66" % (self.lp_info['server'], self.lp_info['key'], self.lp_info['ts'])
            resp = requests.get(url)
            if 'failed' in json.loads(resp.content):              # Если срок действия ключа истек, запрашиваем новый
                self.longpoll_get()
            resp_json = json.loads(resp.content)
            self.lp_info['ts'] = resp_json['ts']
            
            if len(resp_json['updates']) > 0:
                print resp_json
                for n in range(len(resp_json['updates'])):
                    
                    if resp_json['updates'][n][0] == 0:
                        pass
                    elif resp_json['updates'][n][0] == 1:
                        pass
                    elif resp_json['updates'][n][0] == 2:
                        pass
                    elif resp_json['updates'][n][0] == 3:
                        pass
                    elif resp_json['updates'][n][0] == 4:
                        message = {
                            'mid'             : resp_json['updates'][n][1],
                            'flags'           : resp_json['updates'][n][2],
                            'uid'             : resp_json['updates'][n][3],
                            'timestamp'       : resp_json['updates'][n][4],
                            'subj'            : resp_json['updates'][n][5],
                            'text'            : resp_json['updates'][n][6],
                            'attachments'     : resp_json['updates'][n][7]
                        }
                        self.get_history(message=message)
                    elif resp_json['updates'][n][0] == 6:
                        pass
                    elif resp_json['updates'][n][0] == 7:
                        pass
                    elif resp_json['updates'][n][0] == 8:
                        uid = abs(resp_json['updates'][n][1])          # id приходит отрицательным, выравниваем
                        uid = str(uid)
                        print self.get_names(uid)[uid] + u' в сети'
                    elif resp_json['updates'][n][0] == 9:
                        uid = abs(resp_json['updates'][n][1])          # id приходит отрицательным, выравниваем
                        uid = str(uid)
                        print self.get_names(uid)[uid] + u' не в сети'
                    elif resp_json['updates'][n][0] == 51:
                        pass
                    elif resp_json['updates'][n][0] == 61:
                        pass
                    elif resp_json['updates'][n][0] == 62:
                        pass
                    elif resp_json['updates'][n][0] == 70:
                        pass
                    elif resp_json['updates'][n][0] == 80:
                        pass
            else:
                print 'No updates'
        else:
            self.longpoll_get()
            print 'expected lp'
        
    def get_access_token(self, token=None):
        self.set_access_token(token)
    
    def set_access_token(self, token=None):
        if token:
            self.access_token = token
        else:
            print "vkCore: No token here"
    
    def vklogout(self):
        with open('token', 'w') as f:
            f.write('')
        mainf.hide()
        login.show()
    
    def send_message(self):
        mainf.statusbar.showMessage("Сообщение отправляется...")
        row = mainf.ui.dialogList.row(mainf.ui.dialogList.selectedItems()[0])
        st = mainf.ui.messageEdit.toPlainText()
        if mainf.ui.messageEdit.toPlainText() == '':
            mainf.statusbar.showMessage("Введите сообщение!")
        else:
            msg = unicode(mainf.ui.messageEdit.toPlainText())
            try:
                self('messages.send', message=msg, user_id=self.dialogs[row]['user_id'], chat_id=self.dialogs[row]['chat_id'])
            except vk.api.VkAPIMethodError or requests.exceptions.ReadTimeout:
                mainf.statusbar.showMessage("Ошибка при отправке сообщения!")
            else:
                mainf.ui.messageEdit.clear()
                self.get_history()
                mainf.statusbar.showMessage("")
    
    def fetch_dialogs(self, offset=0, more=False):
        mainf.statusbar.showMessage("Обрабатывается...")
        self.diags_json = core('messages.getDialogs', count=200)
        #print diags
        ids = []                                                # список с id пользователей, имя которых надо узнать
        for uid in self.diags_json['items']:
            if not 'chat_id' in uid['message']:
                ids.append(str(uid['message']['user_id']))
                #print uid['message']['user_id']
                #print uid['message']['body']
        #print diags['items']    
        sids = ''
        sids += ','.join(ids)                               # соединяем в строку
        companions = core('users.get', user_ids=sids)       # достаем имена
        coms = []                                           # список с именами пользователей
        for user in companions:                             # формируем этот список
            coms.append(user['first_name'] + ' ' + user['last_name'])

        j = 0
        self.dialogs = []
        print 'len diags: ' + str(len(self.diags_json['items']))
        if not more:
            mainf.ui.dialogList.clear()
            self.dialogs_offset=0
        for i in range(len(self.diags_json['items'])):
            if not 'chat_id' in self.diags_json['items'][i]['message']:
                self.dialogs.append({
                    'caption'       : coms[j],
                    'user_id'       : self.diags_json['items'][i]['message']['user_id'],
                    'chat_id'       : None,
                    'chat_active'   : None
                })
                j += 1
            else:
                
                self.dialogs.append({
                    'caption'       : self.diags_json['items'][i]['message']['title'],
                    'user_id'       : None,
                    'chat_id'       : self.diags_json['items'][i]['message']['chat_id'],
                    'chat_active'   : str(self.diags_json['items'][i]['message']['chat_active'])
                })
         
        for item in self.dialogs:
            mainf.ui.dialogList.addItem(QtGui.QListWidgetItem(item['caption']))
        #mainf.ui.dialogList.addItem(u'Загрузить больше...')
        mainf.statusbar.showMessage("")
    
    def get_names(self, ids=None):
        if ids:
            if type(ids) == list:                                          # если ids получили в виде списка
                sids = ','.join(str(x) for x in ids)
            elif type(ids) == str:
                sids = ids.split(', ')
            elif type(ids) == int:
                sids = str(ids)
            else:
                print 'Error! Incompatible type in get_names()'
            sides = self('users.get', user_ids=sids)                         # достаем имена
            print 'sids: ' + str(sids)
            names = {}                                                       # словарь с именами пользователей и их id
            for unum in range(len(sides)):                                   # формируем этот словарь
                names.update({
                    str(sides[unum]['id'])      : '%s %s' % (sides[unum]['first_name'], sides[unum]['last_name'])
                    #sides[unum]      : sides[unum]['first_name'] + ' ' + sides[unum]['last_name']
                })
                print '%s       %s %s' % (ids[unum], sides[unum]['first_name'], sides[unum]['last_name'])
        print 'members: ' + str(len(names))
        print names
        return names
        
    def get_history(self, message=None):
        mainf.statusbar.showMessage("Обрабатывается...")
        row = mainf.ui.dialogList.row(mainf.ui.dialogList.selectedItems()[0])
        #if row == mainf.ui.dialogList.count() - 1:                      # Нажали на "Загрузить больше..."
            #self.dialogs_offset += 200
            #self.fetch_dialogs(offset=self.dialogs_offset, more=True)
        #else:
        
        if message:
            name = self.get_names(message['uid'])
            item = QtGui.QListWidgetItem('%s %s' % (name, message['text']))
            mainf.ui.messagesList.addItem(item)                             
        else:
            count = 100
            try:
                messages = self('messages.getHistory', rev=1, user_id=self.dialogs[row]['user_id'], chat_id=self.dialogs[row]['chat_id'], count=count)
                messages = self('messages.getHistory', rev=1, user_id=self.dialogs[row]['user_id'], chat_id=self.dialogs[row]['chat_id'], count=count, offset=messages['count']-count)
            except vk.api.VkAPIMethodError as err:
                if str(err)[0] == '6':
                    mainf.statusbar.showMessage("Не так быстро!")
                    print 'Error! Too many requests to server!'
                    return
            else:
                try:
                    messages = self('messages.getHistory', rev=1, user_id=self.dialogs[row]['user_id'], chat_id=self.dialogs[row]['chat_id'], count=count)
                    messages = self('messages.getHistory', rev=1, user_id=self.dialogs[row]['user_id'], chat_id=self.dialogs[row]['chat_id'], count=count, offset=messages['count']-count)
                except requests.exceptions.ReadTimeout:
                    mainf.statusbar.showMessage('Звеняйте, бананiв нема...')
                    print 'Internet connection error'
            
            print 'Dialog selected: chat_id: ' + str(self.dialogs[row]['chat_id']) + '\n                 user_id: ' + str(self.dialogs[row]['user_id'])
                
            if self.dialogs[row]['chat_id']:
                #sids = self.dialogs[row]['chat_active'][1:-1]                    # Это так надо, потому что метод вк возвращает список id СТРОКОЙ, а не списком (с квадратными скобками по бокам)
                sids = []
                for message in messages['items']:
                    if message['user_id'] not in sids:
                        sids.append(message['user_id'])
                names = self.get_names(sids)
                
                
                mainf.ui.messagesList.clear()                # Очистка непосредственно перед отображением новой информации
                print messages['items']
                for m in range(len(messages['items'])):
                    if messages['items'][m]['out'] == 1:
                        if 'attachments' in messages['items'][m]:
                            item = QtGui.QListWidgetItem(profile_info['first_name'] + ' ' + profile_info['last_name'] + u': [вложение]')
                        item = QtGui.QListWidgetItem(profile_info['first_name'] + ' ' + profile_info['last_name'] + ': ' + messages['items'][m]['body'])
                    else:
                        if 'attachments' in messages['items'][m]:
                            item = QtGui.QListWidgetItem(names[str(messages['items'][m]['user_id'])] + u': [вложение]')
                        item = QtGui.QListWidgetItem(names[str(messages['items'][m]['user_id'])] + ': ' + messages['items'][m]['body'])
                    
                    if m % 2 == 0:
                        bgcolor = QtGui.QColor(QtCore.QString('#DAECFF'))
                        item.setBackgroundColor(bgcolor)
                    mainf.ui.messagesList.addItem(item)
            else:
                mainf.ui.messagesList.clear()                # Очистка непосредственно перед отображением новой информации
                print messages['items']
                for m in range(len(messages['items'])):
                    if messages['items'][m]['out'] == 1:
                        item = QtGui.QListWidgetItem(profile_info['first_name'] + ' ' + profile_info['last_name'] + ': ' + messages['items'][m]['body'])
                    else:
                        item = QtGui.QListWidgetItem(self.dialogs[row]['caption'] + ': ' + messages['items'][m]['body'])
                    
                    if m % 2 == 0:
                        bgcolor = QtGui.QColor(QtCore.QString('#DAECFF'))
                        item.setBackgroundColor(bgcolor)
                    mainf.ui.messagesList.addItem(item)
        mainf.ui.messagesList.scrollToItem(mainf.ui.messagesList.item(mainf.ui.messagesList.count()-1))    # прокрутка к последнему сообщению
        mainf.statusbar.showMessage("")

    def prepare_db(filename=None):
        if filename:
            self.db = sqlite3.connect(str(filename))
        else:
            self.db = sqlite3.connect(':memory:')
        self.cur = db.cursor()
        queries = ["CREATE TABLE IF NOT EXISTS users (_id integer PRIMARY KEY AUTOINCREMENT, id integer, f_name text, l_name text, online bool)",
                   "CREATE TABLE IF NOT EXISTS messages (_id integer PRIMARY KEY AUTOINCREMENT, id integer, body text, user_id integer,\
                    from_id integer, date timestamp, read_state bool, out bool, chat_id integer)",
                    "CREATE TABLE IF NOT EXISTS dialogs (_id integer PRIMARY KEY AUTOINCREMENT, caption, user_id, chat_id, chat_active)"]
        try:
            self.cur.execute(query)
        except sqlite3.DatabaseError as err:
            print 'Error:' + err
        else:
            print 'Query success'
            self.db.commit()
        
    
def check_internet():
    url = 'https://vk.com'
    try:
        requests.get(url)
    except requests.exceptions.ConnectionError:
        errbox = QtGui.QMessageBox(text='No Internet connection!')
        errbox.show()
        return False
    else:
        return True


def check_token(token=None):
    print "Checking access token..."
    if not token and check_internet():
        try:
            with open('token', 'r') as f:
                access_token = f.read()
        # А если файла нету, то открываем форму логина и логинимся
        except IOError:
            login.show()
        else:
            if len(access_token) != 85:          # Если длина токена не совпадает с реальной, берем новый
                login.show()
            else:
                print "Read token from file"
                core.set_access_token(access_token)
                mainf.statusbar.showMessage("Online")
                try:
                    mainf.set_title()
                except vk.api.VkAPIMethodError as err:
                    if str(err)[0] == '7' or str(err)[0] == '5':
                        print 'Auth error: invalid token from file'
                        print 'login show'
                        login.show()
                else:
                    core.set_access_token(token)
                    mainf.statusbar.showMessage("Online")
                    mainf.set_title()
                    mainf.show()
                    core.fetch_dialogs()
    elif check_internet():
        core.set_access_token(token)
        mainf.statusbar.showMessage("Online")
        mainf.set_title()
        mainf.show()
        core.fetch_dialogs()
    else:
        print "No Internet connection"
        errbox = QtGui.QMessageBox(text='No Internet connection')



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Для нормального отображения русского текста
    utfcodec = QTextCodec.codecForName('UTF-8')
    QTextCodec.setCodecForTr(utfcodec)
    QTextCodec.setCodecForCStrings(utfcodec)
    app = QtGui.QApplication(sys.argv)
    login = WebLogin()
    core = vkCore()
    mainf = MainForm()                                                  
    check_token()
    sys.exit(app.exec_())