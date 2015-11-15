# -*- coding:utf-8 -*-

import sys
import asyncio
import platform

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from controller_api import ControllerApi
from view_api import ViewOp
from widgets.login_dialog import LoginDialog
from widgets.music_table import MusicTableWidget
from widgets.lyric import LyricWidget
from widgets.playlist_widget import PlaylistItem
from widgets.desktop_mini import DesktopMiniLayer
from widgets.notify import NotifyWidget
from views import UiMainWidget
from plugin import NetEaseMusic, Hotkey
from base.player import Player
from base.network_manger import NetworkManager
from base.utils import func_coroutine
from c.utils import show_start_tip
from c.modes import ModesManger
from constants import WINDOW_ICON


class Controller(QWidget):

    ui = None

    def __init__(self, parent=None):
        super().__init__(parent)
        Controller.ui = UiMainWidget()
        ViewOp.ui = Controller.ui
        ViewOp.controller = ControllerApi
        Controller.ui.setup_ui(self)

        ControllerApi.player = Player()
        ControllerApi.view = ViewOp
        ControllerApi.desktop_mini = DesktopMiniLayer()
        ControllerApi.lyric_widget = LyricWidget()
        ControllerApi.notify_widget = NotifyWidget()

        ControllerApi.network_manager = NetworkManager()
        ControllerApi.current_playlist_widget = MusicTableWidget()

        self._search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        # self._switch_mode_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)

        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setWindowIcon(QIcon(WINDOW_ICON))
        self.setWindowTitle('FeelUOwn')
        self.resize(960, 580)

        self.mode_manager = ModesManger()
        self._init_signal_binding()
        app_event_loop = asyncio.get_event_loop()
        app_event_loop.call_later(1, self._init_plugins)
        show_start_tip()

    def _init_plugins(self):
        NetEaseMusic.init(self)  # 特别意义的插件
        Hotkey.init()

    def _init_signal_binding(self):
        """初始化部分信号绑定
        """
        ViewOp.ui.LOGIN_BTN.clicked.connect(self.pop_login)
        ViewOp.ui.QUIT_ACTION.triggered.connect(sys.exit)
        ViewOp.ui.SONG_PROGRESS_SLIDER.sliderMoved.connect(ControllerApi.seek)
        ViewOp.ui.SHOW_CURRENT_SONGS.clicked.connect(self._show_current_playlist)

        ViewOp.ui.SEARCH_BOX.returnPressed.connect(self._search_music)
        ViewOp.ui.LOVE_SONG_BTN.clicked.connect(ViewOp.on_set_favorite_btn_clicked)
        ViewOp.ui.SIMI_SONGS_BTN.clicked.connect(self.mode_manager.change_to_simi)

        ViewOp.ui.SHOW_DESKTOP_MINI.clicked.connect(self.switch_desktop_mini)

        ViewOp.ui.PLAY_OR_PAUSE.clicked.connect(ViewOp.on_play_or_pause_clicked)

        ViewOp.ui.WEBVIEW.signal_play.connect(self.on_play_song_clicked)
        ViewOp.ui.WEBVIEW.signal_play_songs.connect(self.on_play_songs)
        ViewOp.ui.WEBVIEW.signal_play_mv.connect(ControllerApi.play_mv_by_mvid)
        ViewOp.ui.WEBVIEW.signal_search_album.connect(self.search_album)
        ViewOp.ui.WEBVIEW.signal_search_artist.connect(self.search_artist)

        ViewOp.ui.PLAY_PREVIOUS_SONG_BTN.clicked.connect(ControllerApi.player.play_last)
        ViewOp.ui.PLAY_NEXT_SONG_BTN.clicked.connect(ControllerApi.player.play_next)
        ViewOp.ui.PLAY_MV_BTN.clicked.connect(ViewOp.on_play_current_song_mv_clicked)
        ViewOp.ui.SHOW_LYRIC_BTN.clicked.connect(ControllerApi.toggle_lyric_widget)

        ViewOp.ui.SPREAD_BTN_FOR_MY_LIST.clicked.connect(
            ViewOp.ui.MY_LIST_WIDGET.fold_spread_with_animation)
        ViewOp.ui.SPREAD_BTN_FOR_COLLECTION.clicked.connect(
            ViewOp.ui.COLLECTION_LIST_WIDGET.fold_spread_with_animation)
        ViewOp.ui.SPREAD_BTN_FOR_LOCAL.clicked.connect(
            ViewOp.ui.LOCAL_LIST_WIDGET.fold_spread_with_animation)
        ViewOp.ui.NEW_PLAYLIST_BTN.clicked.connect(ViewOp.new_playlist)

        ControllerApi.player.signal_player_media_changed.connect(ViewOp.on_player_media_changed)
        ControllerApi.player.stateChanged.connect(ViewOp.on_player_state_changed)
        ControllerApi.player.positionChanged.connect(ViewOp.on_player_position_changed)
        ControllerApi.player.durationChanged.connect(ViewOp.on_player_duration_changed)
        ControllerApi.player.signal_playlist_is_empty.connect(self.on_playlist_empty)
        ControllerApi.player.signal_playback_mode_changed.connect(
            ViewOp.ui.STATUS_BAR.playmode_switch_label.on_mode_changed)

        ControllerApi.network_manager.finished.connect(ControllerApi.network_manager.access_network_queue)

        ControllerApi.desktop_mini.content.set_song_like_signal.connect(ViewOp.on_set_favorite_btn_clicked)
        ControllerApi.desktop_mini.content.play_last_music_signal.connect(ControllerApi.player.play_last)
        ControllerApi.desktop_mini.content.play_next_music_signal.connect(ControllerApi.player.play_next)
        ControllerApi.desktop_mini.close_signal.connect(self.show)

        ViewOp.ui.FM_ITEM.signal_text_btn_clicked.connect(self.mode_manager.change_to_fm)

        ControllerApi.current_playlist_widget.signal_play_music.connect(self.on_play_song_clicked)
        ControllerApi.current_playlist_widget.signal_remove_music_from_list.connect(self.remove_music_from_list)

        ControllerApi.current_playlist_widget.resize(500, 200)
        ControllerApi.current_playlist_widget.close()
        ViewOp.ui.PROGRESS.setRange(0, 100)

        ControllerApi.player.signal_download_progress.connect(ViewOp.ui.PROGRESS.setValue)

        self._search_shortcut.activated.connect(ViewOp.ui.SEARCH_BOX.setFocus)
        # self._switch_mode_shortcut.activated.connect(self.switch_desktop_mini)

    def _show_current_playlist(self):
        if ControllerApi.current_playlist_widget.isVisible():
            ControllerApi.current_playlist_widget.close()
            return
        ControllerApi.current_playlist_widget.resize(500, 200)
        width = ControllerApi.current_playlist_widget.width()
        p_width = self.width()

        geometry = self.geometry()
        p_x, p_y = geometry.x(), geometry.y()

        x = p_x + p_width - width
        y = ViewOp.ui.TOP_WIDGET.height() + p_y - 8

        ControllerApi.current_playlist_widget.setGeometry(x, y, 500, 300)
        ControllerApi.current_playlist_widget.show()
        ControllerApi.current_playlist_widget.setFocus(True)

    @pyqtSlot()
    def pop_login(self):
        if ControllerApi.state['is_login'] is False:
            w = LoginDialog(self)
            w.signal_login_sucess.connect(self.on_login_success)
            w.show()

    @pyqtSlot(dict)
    def on_login_success(self, data):
        ControllerApi.set_login()
        ViewOp.load_user_infos(data)

    @func_coroutine
    @pyqtSlot(int)
    def on_play_song_clicked(self, mid=None):
        self.mode_manager.change_to_normal()
        ControllerApi.play_specific_song_by_mid(mid)

    def switch_desktop_mini(self):
        if ControllerApi.desktop_mini.isVisible():
            self.show()
        else:
            if platform.system().lower() == "darwin":
                self.showMinimized()
            else:
                self.hide()
        ControllerApi.toggle_desktop_mini()

    @pyqtSlot(int)
    def on_play_songs(self, songs):
        self.mode_manager.change_to_normal()
        if len(songs) == 0:
            ViewOp.ui.STATUS_BAR.showMessage(u'该列表没有歌曲', 2000)
            return
        ControllerApi.current_playlist_widget.set_songs(songs)
        ControllerApi.player.set_music_list(songs)

    @pyqtSlot(int)
    def remove_music_from_list(self, mid):
        ControllerApi.player.remove_music(mid)

    @pyqtSlot()
    def on_playlist_empty(self):
        ViewOp.ui.SONG_NAME_LABEL.setText(u'当前没有歌曲播放')
        ViewOp.ui.SONG_COUNTDOWN_LABEL.setText('00:00')
        ViewOp.ui.PLAY_OR_PAUSE.setChecked(True)
    
    @staticmethod
    @func_coroutine
    @pyqtSlot(int)
    def search_album(aid):
        album_detail_model = ControllerApi.api.get_album_detail(aid)
        if not ControllerApi.api.is_response_ok(album_detail_model):
            return
        ViewOp.ui.WEBVIEW.load_album(album_detail_model)
        ControllerApi.state['current_pid'] = 0

    @staticmethod
    @func_coroutine
    @pyqtSlot(int)
    def search_artist(aid):
        artist_detail_model = ControllerApi.api.get_artist_detail(aid)
        if not ControllerApi.api.is_response_ok(artist_detail_model):
            return
        ViewOp.ui.WEBVIEW.load_artist(artist_detail_model)
        ControllerApi.state['current_pid'] = 0

    @func_coroutine
    @pyqtSlot()
    def _search_music(self):
        text = ViewOp.ui.SEARCH_BOX.text()
        if text != '':
            ViewOp.ui.STATUS_BAR.showMessage(u'正在搜索: ' + text)
            songs = ControllerApi.api.search(text)
            if not ControllerApi.api.is_response_ok(songs):
                return
            PlaylistItem.de_active_all()
            ViewOp.ui.WEBVIEW.load_search_result(songs)
            ControllerApi.state['current_pid'] = 0
            length = len(songs)
            if length != 0:
                ViewOp.ui.STATUS_BAR.showMessage(u'O(∩_∩)O，搜索到 ' + str(length) + u' 首 ' + text + u' 相关歌曲', 5000)
                return
            else:
                ViewOp.ui.STATUS_BAR.showMessage(u'Oops，没有找到相关歌曲', 5000)
                return

    def paintEvent(self, event):
        """
        self is derived from QWidget, Stylesheets don't work unless \
        paintEvent is reimplemented.y
        at the same time, if self is derived from QFrame, this isn't needed.
        """
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        style = self.style()
        style.drawPrimitive(QStyle.PE_Widget, option, painter, self)
