from eimg_loader import EImgLoader
import ui
from config_loader import ConfigLoader
import threading
from queue import Queue
import console
from ui import Image
from collections import deque
from itertools import islice


url = 'https://e-hentai.org/s/9962198a63/1300988-2'
# url = 'https://m.k886.net/look/name/%E8%84%AB%E5%85%89%E5%85%89%E5%B0%8F%E5%B3%B6/cid/35979/id/331785/p/7#'
# url = 'https://m.k886.net/look/name/%E8%AA%BF%E6%95%99%E5%AE%B6%E6%94%BF%E5%A9%A6/cid/35290/id/323975/p/18'
# url = 'https://raws.mangazuki.co/manga/desire-king/81'
#url = 'https://raws.mangazuki.co/manga/desire-king/48'
# url = "https://raws.mangazuki.co/manga/desire-king/49"

# url = 'https://e-hentai.org/s/d0c15f30ab/1300988-1'
# url = 'http://www.177pic.info/html/2018/04/1999461.html/19'
url = 'https://manhwahand.com/manhwa/desire-king/chapter-1/?style=list'

conf_loader = ConfigLoader()

dict_conf = conf_loader.dict_conf
dict_bm = conf_loader.dict_bookmark


class Reader:
    ITEM_H = 70
    WIDTH_LINE = 337
    LOADING = Image.named('iob:load_d_32')
        
    def __init__(self, scrollview, tableview):
        self.var_ebook_loader = EImgLoader(dict_conf)
        self.has_sent_req = False
        self.scrollview = scrollview
        self.tableview = tableview
        self.queue = Queue()
        self.items = deque(self.scrollview.subviews)
        assert (len(self.items) - 1) * self.ITEM_H > scrollview.height
        self.init_subviews(url)
        
    def load_page(self, init=False):
        contents, title, url = self.var_ebook_loader.get_one_img()
        self.queue.put((contents, title, url, init))
        
    def check_title(self):
        off_set = self.cur_offset
        for item in self.items:
            if item.y + item.height >= off_set:
                i = item.i
                if i is None:
                    continue
                
                for l, r, name, url in self.titles:
                    if l <= i < r:
                        nav_view.name = name
                return
        
    def add2contents(self):
        if not self.queue.empty():
            contents, title, url, init = self.queue.get()
            l = len(self.contents)
            self.contents = self.contents + contents
            r = len(self.contents)
            if self.titles:
                last_title = self.titles[-1]
                if last_title[3] == url:
                    self.titles[-1] = (last_title[0], r, title, url)
                    console.hud_alert('merge')
                else:
                    self.titles.append((l, r, title, url))
            else:
                self.titles.append((l, r, title, url))
                        
            height = 0
            for content in contents:
                height += self.WIDTH_LINE / content.size.x * content.size.y
            if init:
                height -= 10
            self.scrollview.content_size += (0, height)
            self.has_sent_req = False
            return True
        return False
        
    def load_next_page_bg(self):
        if not self.has_sent_req:
            self.has_sent_req = True
            self.t = threading.Thread(target=self.load_page)
            self.t.start()
        
    def init_subviews(self, url, i=0, j=0):
        if self.has_sent_req:
            self.t.join()
        self.has_sent_req = False
        self.queue = Queue()
        scrollview = self.scrollview
        scrollview.content_size = (scrollview.width, 0)
        
        self.cur_offset = 0
            
        self.contents = []
        # (l, r, name)
        self.titles = []
        self.var_ebook_loader.set_url(url)
        self.load_page(True)
        self.add2contents()
        # 条件应该是把一页填充满而且书签模式下尽量加载
        while scrollview.content_size.y <= scrollview.height or len(self.contents) <= i:
            self.load_page()
            self.add2contents()
        # print(scrollview.content_size)
        
        rows = i
        len_content = len(self.contents)
        len_items = len(self.items)
        y = 0
        start = max(0, len_items - len_content)
        remain = islice(self.items, start, len_items)
        for i, (item, content) in enumerate(zip(remain, self.contents)):
            img = content
            img_width, img_height = img.size
            item.height = self.WIDTH_LINE / img_width * img_height
            item.image = img
            item.i = i
            item.y = y
            y += item.height
        
        y = 0
        if len_content < len_items:
            end = len_items - len_content - 1
            for i in range(end, -1, -1):
                item = self.items[i]
                item.i = None
                item.image = None
                y -= item.height
                item.y = y
            
        h = 0
        for content in self.contents[:rows]:
            img = content
            img_width, img_height = img.size
            height = self.WIDTH_LINE / img_width * img_height
            h += height
            
        # print(self.items)
        self.check_title()
        # print(rows, i, j)
        # 这个破玩意儿改了之后会自动调用监听函数
        
        scrollview.content_offset = (0, h+j)
        
    def reset_item_height(self, img, item):
        width = item.width
        img_width, img_height = img.size
        item.height = width / img_width * img_height
        return item.height
        
    def reset_scrollbar(self):
        scrollview = self.scrollview
        offset_x, offset_y = scrollview.content_offset
        max_offset = scrollview.content_size.y - scrollview.height
        cur_offset = offset_y
        min_offset = min(cur_offset, max_offset)
        scrollview.content_offset = (offset_x, min_offset)
        
    def scrollview_did_scroll(self, scrollview):
        offset = scrollview.content_offset.y
        is_scroll_down = True if offset > self.cur_offset else False
        self.cur_offset = offset
        
        reader_h = scrollview.height
        # print('t')
        
        # 滚动条下移
        if is_scroll_down:
            y = self.scrollview.content_size[1]
            if y and self.cur_offset / y >= 0.8:
                pass
            while True:
                item_end = self.items[-1]
                item = self.items[0]
                if (item_end.y + item_end.height - reader_h <= offset and item_end.i is not None):
                    console.hud_alert('应该load')
                    i = item_end.i + 1
            
                    if i >= len(self.contents):
                        img = self.LOADING
                        self.load_next_page_bg()
                        i = None
                        
                    else:
                        img = self.contents[i]
                        
                    item.image = img
                    item.y = item_end.y + item_end.height
                    self.reset_item_height(img, item)
                    item.i = i
                    self.items.rotate(-1)
                elif item_end.i is None and item_end.y <= offset + reader_h:
                    console.hud_alert(f'应该refresh')
                    if not self.add2contents():
                        break
                                    
                    item = self.items[-2]
                    i = item.i + 1
            
                    if i < len(self.contents):
                        img = self.contents[i]
                        
                        item_end.image = img
                        item_end.y = item.y + item.height
                        self.reset_item_height(img, item_end)
                        item_end.i = i
                    # 这个防止空白页吧……会有吗？
                    else:
                        break
                else:
                    break
        else:
            while True:
                item = self.items[-1]
                item_start = self.items[0]
                if item_start.y >= offset:
                    # None的时候仅仅是初始化设计导致的
                    if item_start.i is None or item_start.i <= 0:
                        break
                    i = item_start.i - 1
                    img = self.contents[i]
                    item.image = img
                    
                    item.y = item_start.y - self.reset_item_height(img, item)
                    item.i = i
                    self.items.rotate(1)
                    
                else:
                    break
        self.check_title()
        

class BMTableViewer:
    def __init__(self, reader):
        self.reader = reader
        
    def tableview_did_select(self, tableview, section, row):
        bm = tableview.data_source.items[row]
        tableview.reload()
        self.reader.init_subviews(bm['url'], bm['i'], bm['j'])
        nav_view.pop_view()
        ui.animate(self.reader.reset_scrollbar, 0.5)
        # nav_view.right_button_items = main_button_items
                    
    def save_bm(self, sender):
        scrollview = self.reader.scrollview
        off_set = scrollview.content_offset.y
        # !!!!!!!!!
        for item in self.reader.items:
            if item.y + item.height >= off_set:
                i = item.i
                j = off_set - item.y
                break
        if i is None:
            return
        for l, r, name, url in self.reader.titles:
            if l <= i < r:
                # 本页的i 相对段落数目
                new_bookmark = {
                    'i': i - l,
                    'j': j,
                    'url': url,
                    'title': name
                }
                print(new_bookmark)
                        
        is_duplicated = conf_loader.check_bookmark(new_bookmark)
        
        if not is_duplicated:
            self.reader.tableview.data_source.items.append(new_bookmark)
            conf_loader.refresh_file(self.reader.tableview.data_source)
            console.hud_alert(f'已经保存')
        else:
            console.hud_alert('重复操作')
    

# url = input('请输入:\n')
reader_view = ui.load_view('eimg_reader')
sc = reader_view['scrollview']
bm_view = ui.load_view('bookmark')
nav_view = ui.NavigationView(reader_view)
tb = bm_view['tableview']

tb.data_source.items = dict_bm['bookmarks']
tb.data_source.edit_action = conf_loader.refresh_file

for i in range(9):
    # print(reader_view[f'imageview{i}'])
    sc.add_subview(reader_view[f'imageview{i}'])

var = Reader(sc, tb)
var_bm_table_viewer = BMTableViewer(var)

sc.delegate = var
tb.delegate = var_bm_table_viewer

reader_view['button_save_bm'].action = var_bm_table_viewer.save_bm

nav_view.navigation_bar_hidden = True
nav_view.present('fullscreen')
return_button_item = ui.ButtonItem(image=Image.named('iob:arrow_return_left_24'))
bm_button_items = [return_button_item]
nav_view.right_button_items = bm_button_items
return_button_item.action = nav_view.pop_view
reader_view['button_show_bm'].action = lambda _: nav_view.push_view(bm_view)

menu_button_item = ui.ButtonItem(image=Image.named('iob:navicon_round_24'))
main_button_items = [menu_button_item]
menu_button_item.action = nav_view.pop_view
        

