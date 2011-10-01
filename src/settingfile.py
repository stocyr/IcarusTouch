'''
TouchContinuum

Copyright (C) 2011  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of TouchContinuum.

TouchContinuum is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

TouchContinuum is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with TouchContinuum.  If not, see <http://www.gnu.org/licenses/>.
'''


from kivy.properties import ObjectProperty, StringProperty, ListProperty

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.settings import SettingItem
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView


'''
####################################
##
##   SettingsFile
##   Custom SettingItem class to select a file
##
####################################
'''
class SettingFile(SettingItem):
    '''Implementation of a file choose setting in top of :class:`SettingItem`.
    The choosen file is showed in a Label, but when you click on it, a Popup
    window will open with a fileChooser in a scrollView, available to set a custom value.
    '''
    
    file_filter = ListProperty([])
    
    path = StringProperty(None)

    popup = ObjectProperty(None, allownone=True)
    '''(internal) Used to store the current popup when it's showed

    :data:`popup` is a :class:`~kivy.properties.ObjectProperty`, default to
    None.
    '''

    textinput = ObjectProperty(None)
    '''(internal) Used to store the current textinput from the popup, and listen
    for any changes.

    :data:`popup` is a :class:`~kivy.properties.ObjectProperty`, default to
    None.
    '''

    def on_panel(self, instance, value):
        if value is None:
            return
        self.bind(on_release=self._create_popup)

    def _validate(self, instance):
        self.popup.dismiss()
        self.popup = None
        value = self.fileChooser.selection
        # if the value was empty, don't change anything.
        if value == None or value == '':
            return
        self.value = value
    
    def _create_popup(self, instance):
        # create popup layout containing a boxLayout
        content = BoxLayout(orientation='vertical', spacing=5)
        self.popup = popup = Popup(title=self.title,
            content=content, size_hint=(None, None), size=(600, 400))
        
        # first, create the scrollView
        self.scrollView = scrollView = ScrollView()
        
        # then, create the fileChooser and integrate it in the scrollView
        self.fileChooser = fileChooser = FileChooserListView(#path=self.path, --> causes errors!
                                                             filters=self.file_filter,
                                                             size_hint_y=None)
        fileChooser.height = 500   # TODO: UGLY!
        scrollView.add_widget(fileChooser)
        
        # construct the content, widget are used as a spacer
        content.add_widget(Widget(size_hint_y=None, height=5))
        content.add_widget(scrollView)
        content.add_widget(Widget(size_hint_y=None, height=5))
        
        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        
        btn = Button(text='Cancel')
        btn.bind(on_release=popup.dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)
        
        # all done, open the popup !
        popup.open()
