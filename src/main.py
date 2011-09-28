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


import pygame.midi

import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.config import Config
# for making screenshots with F12:
Config.set('modules', 'keybinding', '')
from kivy.base import EventLoop
from kivy.animation import Animation
from kivy.properties import ObjectProperty, NumericProperty, StringProperty

from kivy.uix.image import Image
from kivy.uix.widget import Widget

from settingfile import SettingFile
from settingmidi import SettingMIDI
from keyboard import Keyboard
from mysettingspanel import MySettingsPanel


'''
####################################
##
##   GLOBAL SETTINGS
##
####################################
'''

VERSION = '1.0'

# Key Graphics
# ---------------------------------------------------------
KEY_WIDTH = 50

# Circle Graphics
# ---------------------------------------------------------
#CIRCLE_IMAGE_FADEOUT_SIZE = CIRCLE_IMAGE_SIZE * 2 --> hard-wired in the code to 2
CIRCLE_IMAGE_FADEOUT_TIME = 2.0
CIRCLE_IMAGE_COLOR = (.7, .85, 1, 1)
CIRCLE_IMAGE_COLOR_TRANSPARENT = (.7, .85, 1, 0)

# Keyboard Functionality
# ---------------------------------------------------------
BORDER_WIDTH = 145
KEYBOARD_CHAGE_DURATION = 0.5
SCROLLING_STICKY_FACTOR = 0.3
KEYBOARD_ANIMATION_X_DURATION = 0.5

SCALE_KEYWIDTH_THRESHOLD = 2
SCALE_KEYWIDTH_FACTOR = 3

# Background Functionality
# ---------------------------------------------------------
BACKGROUND_CHANGE_DURATION = 0.3


class Background(Image):
    background_x_animation = Animation()
    old_background_change_animation = Animation()
    new_background_change_animation = Animation()
    background_is_animated = False


class Feedback(Image):
    feedback_animation = Animation()
    transparency = NumericProperty(None)


'''
####################################
##
##   Main Widget Class
##
####################################
'''
class TouchContinuumWidget(Widget):
    app = ObjectProperty(None)
    float_layout = ObjectProperty(None)
    pitch_lock_button = ObjectProperty(None)
    y_axis_volume_button = ObjectProperty(None)
    setting_button = ObjectProperty(None)
    look_button = ObjectProperty(None)
    feedback_wall = ObjectProperty(None)
    scale_keywidth_touch_positions = {}
    version = StringProperty(VERSION)
    
    
    '''
    ####################################
    ##
    ##   Class Initialisation
    ##
    ####################################
    '''
    def __init__(self, **kwargs):
        super(TouchContinuumWidget, self).__init__(**kwargs) # don't know if this is necessary?
        
        # add background image (and add it in the BACKGROUND! --> index modification)
        self.background = Background(source=self.app.config.get('Graphics', 'Background'))
        self.float_layout.add_widget(self.background, index=len(self.float_layout.children))
        
        # add feedback wall image
        self.feedback_wall = Feedback(
            source='images/feedbackwall.png',
            transparency=0)
        self.float_layout.add_widget(self.feedback_wall)
        
        # add the keyboard itself
        my_key_width = KEY_WIDTH
        self.keyboard = Keyboard(
            source=self.app.config.get('Graphics', 'Keyboard'),
            pos=(-540, 366),
            size=(12*5*my_key_width, 468), #468 if self.get_parent_window().height > 
            border_width=BORDER_WIDTH,
            key_width=my_key_width)
        self.add_widget(self.keyboard)
        
        # initialize the midi device
        pygame.midi.init()
        self.set_midi_device()
        
        # initialize the settings_panel (I'm doing this here, otherwise opening it in real-time takes ages...)
        self.my_settings_panel = MySettingsPanel()
    
    
    '''
    ####################################
    ##
    ##   On Touch Down
    ##
    ####################################
    '''
    def on_touch_down(self, touch):
        ud = touch.ud
        
        # find out the touchs "function":  
        if self.my_settings_panel.is_open == True:
            
            if self.my_settings_panel.keyboard_scroll_view_box.collide_point(*touch.pos) or \
                self.my_settings_panel.background_scroll_view_grid.collide_point(*touch.pos):
                ud['settingspanel'] = True
                return super(TouchContinuumWidget, self).on_touch_down(touch)
            
            else:
                # user has clicked aside - he wants to quit the settings.
                self.remove_widget(self.my_settings_panel)
                self.my_settings_panel.is_open = False
                return True
            
        elif self.keyboard.collide_point(*touch.pos):
            return super(TouchContinuumWidget, self).on_touch_down(touch)
        
        elif self.pitch_lock_button.collide_point(*touch.pos) or \
            self.y_axis_volume_button.collide_point(*touch.pos) or \
            self.look_button.collide_point(*touch.pos) or \
            self.settings_button.collide_point(*touch.pos):
            self.create_circle(touch)
            return super(TouchContinuumWidget, self).on_touch_down(touch)
            
        # if it wasn't a button nor a key touch, its a scroll touch.
        for search_touch in EventLoop.touches[:]:
                    # but if there is already another touch in scroll mode (and not already in 'scale' mode), maybe the desired action is 'scale' not 'scroll'
                    if 'scroll' in search_touch.ud and not self.scale_keywidth_touch_positions:
                        # remember their actual positions
                        self.scale_keywidth_touch_positions = {'initial_first': search_touch.x, 'initial_second': touch.x, 'first_touch': search_touch, 'second_touch': touch}
                        print 'multiple saving position data'
        
        ud['scroll'] = True
        
        # if there is an keyboard "spring back" animation in progress, stop it.
        self.keyboard.keyboard_x_animation.stop(self.keyboard)
    
    
    '''
    ####################################
    ##
    ##   On Touch Move
    ##
    ####################################
    '''
    def on_touch_move(self, touch):
        ud = touch.ud
        
        
        # if there are two fingers in scroll mode (thus the dict 'scale_keywidth_touch_positions' isn't empty) - maybe he wants to scale the keywidth?   
        scalepos = self.scale_keywidth_touch_positions
        if scalepos:
            delta_first_touch = scalepos['first_touch'].x - scalepos['initial_first']
            delta_second_touch = scalepos['second_touch'].x - scalepos['initial_second']
            
            print 'move: delta_first = %s, delta_second = %s' % (delta_first_touch, delta_second_touch)
            
            # if the user dragged both touches towards each other or vice versa
            if (delta_first_touch > SCALE_KEYWIDTH_THRESHOLD and delta_second_touch > -SCALE_KEYWIDTH_THRESHOLD) or \
                (delta_first_touch > -SCALE_KEYWIDTH_THRESHOLD and delta_second_touch > SCALE_KEYWIDTH_THRESHOLD):
                print 'scale mode!'
                
                # if the first touch was on the left and the user moved it right OR it was right and moved to the left, we want to make the keywidth smaller
                if (scalepos['initial_first'] < scalepos['initial_second'] and delta_first_touch > 0) or \
                    (scalepos['initial_first'] > scalepos['initial_second'] and delta_first_touch < 0):
                    print 'zoom out'
                    # perform a ZOOM OUT with a factor applied to the delta_touch_distance:
                    delta_touch_distance = abs(delta_first_touch + (-delta_second_touch))
                    #self.keyboard.key_width -= int(delta_touch_distance / SCALE_KEYWIDTH_FACTOR)
                    #self.keyboard.width = 12*5*self.keyboard.key_width
                    
                # if the first touch was on the left and the user moved it left OR it was right and moved to the right, we want to make the keywidth smaller
                elif (scalepos['initial_first'] < scalepos['initial_second'] and delta_first_touch < 0) or \
                    (scalepos['initial_first'] > scalepos['initial_second'] and delta_first_touch > 0):
                    print 'zoom in'
                    # perform a ZOOM IN in with a factor applied to the delta_touch_distance:
                    delta_touch_distance = abs(delta_first_touch + (-delta_second_touch))
                    #self.keyboard.key_width += int(delta_touch_distance / SCALE_KEYWIDTH_FACTOR)
                    #self.keyboard.width = 12*5*self.keyboard.key_width
        
                
        elif 'scroll' in ud:
            # move keyboard left or right. Make sure to move also the shadow border around it
            # nice side effect: if there is more than 1 touch in 'scroll' mode, scrolling is faster!
            
            # is an animation in progress?`--> stop it.
            #self.keyboard.keyboard_x_animation.stop()
            
            # if the end of the keyboard is visible, scroll slower!
            scroll_factor = 1
            
            if self.keyboard.x > 0 or self.keyboard.x < (self.get_parent_window().width - self.keyboard.width):
                counter = 0
                for touch in EventLoop.touches[:]:
                    if 'scroll' in touch.ud:
                        counter += 1 # how many touches are in 'scroll' mode?
                
                # if there is more than one touch in scroll mode, i don't want the factor to grow!
                scroll_factor = SCROLLING_STICKY_FACTOR / counter
            
            self.keyboard.x += touch.dx * scroll_factor
            return
        
        # if the touch was started on the keyboard
        if 'initial_key' in ud or 'settingspanel' in ud:
            return super(TouchContinuumWidget, self).on_touch_move(touch)
    
    
    '''
    ####################################
    ##
    ##   On Touch Up
    ##
    ####################################
    '''
    def on_touch_up(self, touch):
        ud = touch.ud
        
        #@@@@@@@@@@@@@@@@
        # Scroll Touch
        #@@@@@@@@@@@@@@@@
        
        # if there has been scale mode active or perhaps happening: (better would be: "and there aren't multiple 'scroll' mode touches active anymore
        if self.scale_keywidth_touch_positions:
            # delete all scale mode variables
            print 'deleting the position data'
            self.scale_keywidth_touch_positions = {}
        
        if 'scroll' in ud:
            win = self.get_parent_window()
            # if keyboard end is visible and the touch is released, "jump" on old place:
            if self.keyboard.x > 0:
                self.keyboard.keyboard_x_animation = Animation(x=0, t='out_cubic', duration=KEYBOARD_ANIMATION_X_DURATION)
                self.keyboard.keyboard_x_animation.start(self.keyboard)
            elif self.keyboard.x < (win.width - self.keyboard.width):
                self.keyboard.keyboard_x_animation = Animation(x=win.width - self.keyboard.width, t='out_cubic', duration=KEYBOARD_ANIMATION_X_DURATION)
                self.keyboard.keyboard_x_animation.start(self.keyboard)
        
        if 'initial_key' in ud:
            return super(TouchContinuumWidget, self).on_touch_up(touch)
    
    
    '''
    ####################################
    ##
    ##   Other GUI Events
    ##
    ####################################
    '''
    def on_y_axis_volume_button_press(self):
        if self.y_axis_volume_button.state == 'down':
            self.app.config.set('General', 'YAxis', 'Volume')
            # lock aftertouch to 0:
            self.midi_out.write_short(0xD0, 0)
        else:
            self.app.config.set('General', 'YAxis', 'Aftertouch')
            # lock Y-modulation to 0?
            self.midi_out.write_short(0xB0, 1, 127)
    
    def on_pitch_lock_button_press(self):
        if self.pitch_lock_button.state == 'down':
            self.app.config.set('General', 'PitchLock', 'On')
        else:
            self.app.config.set('General', 'PitchLock', 'Off')
    
    def open_settings(self):
        self.app.open_settings()
    
    
    '''
    ####################################
    ##
    ##   Graphical Functions
    ##
    ####################################
    '''
    def create_circle(self, touch):
        circle = Image(
            source=self.app.config.get('Advanced', 'CircleImage'),
            color=CIRCLE_IMAGE_COLOR,
            allow_stretch=True,
            size=(self.app.config.getint('Advanced', 'CircleSize'), self.app.config.getint('Advanced', 'CircleSize')))
        
        circle.x = touch.x - circle.size[0] / 2
        circle.y = touch.y - circle.size[1] / 2
        
        self.add_widget(circle)
        
        # and just right fade it out after displayed
        animation = Animation(
            color=CIRCLE_IMAGE_COLOR_TRANSPARENT,
            size=(self.app.config.getint('Advanced', 'CircleSize') * 2, self.app.config.getint('Advanced', 'CircleSize') * 2),
            x=circle.pos[0] - (self.app.config.getint('Advanced', 'CircleSize')/2), # workarround for centering the image during resizing
            y=circle.pos[1] - (self.app.config.getint('Advanced', 'CircleSize')/2), # workarround for centering the image during resizing
            t='out_expo', duration=CIRCLE_IMAGE_FADEOUT_TIME)
        
        animation.start(circle)
        animation.bind(on_complete=self.circle_fadeout_complete)
    
    def circle_fadeout_complete(self, animation, widget):
        self.remove_widget(widget)
    
    
    '''
    ####################################
    ##
    ##   Settings Functions
    ##
    ####################################
    '''
    def set_midi_device(self):
        # take the midi device of the settings file and try to connect to it.
        # If there isn't such a device, connect to the default one.
        
        c = pygame.midi.get_count()
        id_device_from_settings = -1
        #print '%s midi devices found' % c
        for i in range(c):
            #print '%s name: %s input: %s output: %s opened: %s' % (pygame.midi.get_device_info(i))
            if pygame.midi.get_device_info(i)[1] == self.app.config.get('MIDI', 'Device'):
                # if the device from the settings exists in the computers list, take that!
                id_device_from_settings = i
        
        #print 'Default is %s' % pygame.midi.get_device_info(pygame.midi.get_default_output_id())[1]
        
        if id_device_from_settings <> -1:
            self.midi_device = id_device_from_settings
            print 'MIDI device "%s" found. Connecting.' % pygame.midi.get_device_info(id_device_from_settings)[1]
        else:
            # if it was not in the list, take the default one
            self.midi_device = pygame.midi.get_default_output_id()
            print 'Warning: No MIDI device named "%s" found. Choosing the system default ("%s").' % (self.app.config.get('MIDI', 'Device'), pygame.midi.get_device_info(self.midi_device)[1])
        
        if pygame.midi.get_device_info(self.midi_device)[4] == 1:
            print 'Error: Can''t open the MIDI device - It''s already opened!'
            
        self.midi_out = pygame.midi.Output(self.midi_device)
    
    
    def open_my_settings_panel(self):
        self.add_widget(self.my_settings_panel)
        
        # bind the background images to function
        for child in self.my_settings_panel.background_scroll_view_grid.children:
            child.bind(on_press=self.background_image_change)
        
        # bind the keyboard images to function
        for child in self.my_settings_panel.keyboard_scroll_view_box.children:
            child.bind(on_press=self.keyboard_image_change)
        
        self.my_settings_panel.is_open = True  
    
    
    def background_image_change(self, dispatcher):
        old_background_instance = self.background
        
        # if the last background change is stil in progress, stop it and start the new.
        if old_background_instance.background_is_animated == True:
            old_background_instance.new_background_change_animation.stop(old_background_instance.new_background_instance)
            old_background_instance.old_background_change_animation.stop(old_background_instance)
            
            self.float_layout.remove_widget(old_background_instance)
            old_background_instance.new_background_instance.color = (1, 1, 1, 1)
            old_background_instance = old_background_instance.new_background_instance
        
        old_background_instance.new_background_instance = Background(
            source=dispatcher.background_normal,
            color=(1, 1, 1, 0))
        self.float_layout.add_widget(old_background_instance.new_background_instance, index=len(self.float_layout.children))
        
        # keep the settings panel on the front
        self.remove_widget(self.my_settings_panel)
        self.add_widget(self.my_settings_panel)
        
        
        old_background_instance.new_background_change_animation = Animation(color=(1, 1, 1, 1), duration=BACKGROUND_CHANGE_DURATION)
        old_background_instance.old_background_change_animation = Animation(color=(1, 1, 1, 0), duration=BACKGROUND_CHANGE_DURATION)
        
        old_background_instance.new_background_change_animation.start(old_background_instance.new_background_instance)
        old_background_instance.old_background_change_animation.start(old_background_instance)
        
        old_background_instance.background_is_animated = True
        old_background_instance.new_background_change_animation.bind(on_complete=self.background_change_complete)
    
    
    def background_change_complete(self, animation, widget):
        # first remove the old background from the widget tree
        self.remove_widget(self.background)
        
        # then make the self.background reference refer to the new background
        self.background = widget
        
        self.background.background_is_animated = False
    
    
    def keyboard_image_change(self, dispatcher):
        win = self.get_parent_window()
        
        old_keyboard_instance = self.keyboard
        
        # if the last keyboard change is stil in progress, stop it and start the new.
        if old_keyboard_instance.keyboard_is_animated == True:
            old_keyboard_instance.new_keyboard_change_animation.stop(old_keyboard_instance.new_keyboard_instance)
            old_keyboard_instance.old_keyboard_change_animation.stop(old_keyboard_instance)
            
            self.remove_widget(old_keyboard_instance)
            old_keyboard_instance.new_keyboard_instance.y = 366
            old_keyboard_instance = old_keyboard_instance.new_keyboard_instance
        
        old_keyboard_instance.new_keyboard_instance = Keyboard(
            source=dispatcher.background_normal,
            pos=(old_keyboard_instance.x, win.height + BORDER_WIDTH),
            size=(self.keyboard.width, old_keyboard_instance.height),
            key_width=old_keyboard_instance.key_width,
            border_width=BORDER_WIDTH)
        self.add_widget(old_keyboard_instance.new_keyboard_instance)
        
        # keep the settings panel on the front
        self.remove_widget(self.my_settings_panel)
        self.add_widget(self.my_settings_panel)
        
        
        old_keyboard_instance.new_keyboard_change_animation = Animation(y=366, t='out_back', duration=KEYBOARD_CHAGE_DURATION)
        old_keyboard_instance.old_keyboard_change_animation = Animation(y=-(self.keyboard.height + BORDER_WIDTH), t='out_back', duration=KEYBOARD_CHAGE_DURATION)
        
        old_keyboard_instance.new_keyboard_change_animation.start(old_keyboard_instance.new_keyboard_instance)
        old_keyboard_instance.old_keyboard_change_animation.start(old_keyboard_instance)
        
        old_keyboard_instance.keyboard_is_animated = True
        old_keyboard_instance.new_keyboard_change_animation.bind(on_complete=self.keyboard_change_complete)
    
    
    def keyboard_change_complete(self, animation, widget):
        # first remove the old keyboard from the widget tree
        self.remove_widget(self.keyboard)
        
        # then make the self.keyboard reference refer to the new keyboard
        self.keyboard = widget
        
        self.keyboard.keyboard_is_animated = False


'''
####################################
##
##   Main Application Class
##
####################################
'''
class TouchContinuum(App):
    title = 'TouchContinuum'
    icon = 'icon.png'
    
    
    def build(self):
        print '\nTouchContinuum v%s  Copyright (C) 2011  Cyril Stoller' % VERSION
        print 'This program comes with ABSOLUTELY NO WARRANTY'
        print 'This is free software, and you are welcome to redistribute it'
        print 'under certain conditions; see the source code for details.\n'
        
        '''
        root = Popup(title='Loading images',
                      content=Label(text='Please wait...'),
                      size_hint=(None, None),
                      size=(400, 400))
        '''
        print 'Loading images... Please wait.'
        
        self.touchcontinuumwidget = TouchContinuumWidget(app=self)
        return self.touchcontinuumwidget
    
   
    def build_config(self, config):
        config.add_section('General')
        config.set('General', 'YAxis', 'Aftertouch')
        config.set('General', 'PitchLock', 'Off')
        config.set('General', 'MonoMode', 'Legato') # inactive if voice mode is 'polyphonic'
        
        
        config.add_section('Graphics')
        config.set('Graphics', 'Keyboard', 'keyboards/keyboard_blue2_shadow.png')
        config.set('Graphics', 'Background', 'backgrounds/cold blue/background_blue_cold3.jpg')

        
        config.add_section('MIDI')
        config.set('MIDI', 'Device', 'USB Uno MIDI Interface')
        config.set('MIDI', 'Channel', '0')
        config.set('MIDI', 'VoiceMode', 'Polyphonic')
        config.set('MIDI', 'PitchbendRange', '24')
        config.set('MIDI', 'Transpose', '36')
        config.set('MIDI', 'CCController', '1') # inactive if y-axis is 'aftertouch'
        
        
        config.add_section('Advanced')
        config.set('Advanced', 'BlobImage', 'images/blob_blue.png')
        config.set('Advanced', 'BlobSize', '60')
        config.set('Advanced', 'CircleImage', 'images/circle.png')
        config.set('Advanced', 'CircleSize', '60')
        config.set('Advanced', 'KeyImage', 'images/key_sw.png')
        
        config.set('Advanced', 'RoundingSchedulerInterval', '0.01')
        config.set('Advanced', 'RoundSpeedToFinger', '0.6')
        config.set('Advanced', 'RoundSpeedToKey', '0.2')
        config.set('Advanced', 'MovementDecay', '0.2')
        
        config.set('Advanced', 'ShowPitchLine', 'Off')
    
    
    def build_settings(self, settings):
        settings.register_type('midi', SettingMIDI)
        settings.register_type('file', SettingFile)
        
        settings.add_json_panel(
            'General', self.config, data='''[
                    { "type": "options", "title": "Y axis", "desc": "MIDI modulation based on the Y axis", "section": "General", "key": "YAxis", "options": ["Aftertouch", "Volume"]},
                    { "type": "bool", "title": "Pitch lock", "desc": "Lock the pitch to chromatic keys", "section": "General", "key": "PitchLock", "values": ["Off", "On"]},
                    { "type": "options", "title": "* Monophony mode", "desc": "Play the keys legato or re-hit them everytime. Only active when the voice mode (under MIDI) are set to Monophonic.", "section": "General", "key": "MonoMode", "options": ["Legato", "Monophonic"]},
                    { "type": "title", "title": "(Settings marked with a * are not yet implemented)" }
            ]''')
        
        settings.add_json_panel(
            'Graphics', self.config, data='''[
                    { "type": "file", "title": "Keyboard", "desc": "Image used as keyboard", "section": "Graphics", "key": "Keyboard", "file_filter": ["*.png", "*.jpg"], "path": "keyboards"},
                    { "type": "file", "title": "Background", "desc": "Image used as background", "section": "Graphics", "key": "Background", "file_filter": ["*.png", "*.jpg"], "path": "backgrounds"},
                    { "type": "title", "title": "(Settings marked with a * are not yet implemented)" }
            ]''')
        
        settings.add_json_panel(
            'MIDI', self.config, data='''[
                    { "type": "midi", "title": "MIDI output device", "desc": "Device to use for MIDI", "section": "MIDI", "key": "Device"},
                    { "type": "numeric", "title": "MIDI channel", "desc": "MIDI channel to send data to [0 - 15]", "section": "MIDI", "key": "Channel"},
                    { "type": "options", "title": "* Voice mode", "desc": "Polyphony mode", "section": "MIDI", "key": "VoiceMode", "options": ["Monophonic", "Polyphonic"]},
                    { "type": "numeric", "title": "Pitch bend range", "desc": "Set the pitch bend range of your synthesizer here (set it as high as possible!) [in half tones]", "section": "MIDI", "key": "PitchbendRange"},
                    { "type": "numeric", "title": "Transpose", "desc": "Transpose the keyboard [in half tones, only positive!]", "section": "MIDI", "key": "Transpose"},
                    { "type": "numeric", "title": "CC controller", "desc": "CC controller to use for changing the volume with the y axis [1 - 127]", "section": "MIDI", "key": "CCController"},
                { "type": "title", "title": "(Settings marked with a * are not yet implemented)" }
            ]''')
        
        settings.add_json_panel(
            'Advanced', self.config, data='''[
                { "type": "title", "title": "Advanced graphic settings" },
                    { "type": "file", "title": "Blob Image", "desc": "Sets the image for the blob representation", "section": "Advanced", "key": "BlobImage", "file_filter": "*.png", "path": "images"},
                    { "type": "numeric", "title": "Blob image size", "desc": "Sets size of the blob image", "section": "Advanced", "key": "BlobSize"},
                    { "type": "file", "title": "Circle image", "desc": "Sets the image for the circle appearing over the settings buttons", "section": "Advanced", "key": "CircleImage", "file_filter": ["*.png", "*.jpg"], "path": "images"},
                    { "type": "numeric", "title": "Circle image size", "desc": "Sets the size of the circle image", "section": "Advanced", "key": "CircleSize"},
                    { "type": "file", "title": "Key illumination image", "desc": "Sets the image of the key illumination (used for illustrating the y axis position on the key)", "section": "Advanced", "key": "KeyImage", "file_filter": "*.png", "path": "images"},
                { "type": "title", "title": "Advanced rounding settings" },
                    { "type": "numeric", "title": "Rounding scheduler interval", "desc": "How fast the rounding algorithm updates the pitch value", "section": "Advanced", "key": "RoundingSchedulerInterval"},
                    { "type": "numeric", "title": "Round speed to finger position", "desc": "How fast the tone snaps to the finger if moved", "section": "Advanced", "key": "RoundSpeedToFinger"},
                    { "type": "numeric", "title": "Round speed to key", "desc": "How fast the tone snaps to the middle of the key if movement has stopped", "section": "Advanced", "key": "RoundSpeedToKey"},
                    { "type": "numeric", "title": "Movement decay time", "desc": "How long you have to wait after finger movement to have the tone snapped to the key", "section": "Advanced", "key": "MovementDecay"},
                { "type": "title", "title": "Debug section" },
                    { "type": "bool", "title": "Show pitch line", "desc": "Show a line that indicates the pitch sent to the MIDI device", "section": "Advanced", "key": "ShowPitchLine", "values": ["Off", "On"]},
                { "type": "title", "title": "(Settings marked with a * are not yet implemented)" }
            ]''')
        
    
    def on_config_change(self, config, section, key, value):
        token = (section, key)
        
        if token == ('General', 'YAxis'):
            self.touchcontinuumwidget.y_axis_volume_button.state = 'normal' if value == 'Aftertouch' else 'down'
            self.touchcontinuumwidget.on_y_axis_volume_button_press()
        elif token == ('General', 'PitchLock'):
            self.touchcontinuumwidget.pitch_lock_button.state = 'normal' if value == 'Off' else 'down'
            self.touchcontinuumwidget.on_pitch_lock_button_press()
        elif token == ('General', 'MonoMode'): # inactive if voice mode is 'polyphonic'
            pass
        
        
        elif token == ('Graphics', 'Background'):
            self.touchcontinuumwidget.background_image_change(value)
        elif token == ('Graphics', 'Keyboard'):
            self.touchcontinuumwidget.keyboard_image_change(value)
        
        
        elif token == ('MIDI', 'Device'):
            self.touchcontinuumwidget.set_midi_device()
        elif token == ('MIDI', 'Channel'):
            # setting the value to 0 here causes an error?!
            pass
        elif token == ('MIDI', 'VoiceMode'):
            pass
        elif token == ('MIDI', 'PitchbendRange'):
            pass
        elif token == ('MIDI', 'Transpose'):
            pass
        elif token == ('MIDI', 'CCController'): # inactive if y-axis is 'aftertouch'
            pass
        
        
        elif token == ('Advanced', 'BlobImage'):
            pass
        elif token == ('Advanced', 'BlobSize'):
            pass
        elif token == ('Advanced', 'CircleImage'):
            pass
        elif token == ('Advanced', 'CircleSize'):
            pass
        elif token == ('Advanced', 'KeyImage'):
            pass
        elif token == ('Advanced', 'InitialRound'):
            pass
        elif token == ('Advanced', 'RoundingSchedulerInterval'):
            pass
        elif token == ('Advanced', 'RoundSpeedToFinger'):
            pass
        elif token == ('Advanced', 'RoundSpeedToKey'):
            pass
        elif token == ('Advanced', 'MovementDecay'):
            pass
        elif token == ('Advanced', 'ShowPitchLine'):
            pass
    
    def print_widget_tree(self):
        print '#################################'
        print '##         Widget Tree         ##'
        print '#################################\n'

        for child in self.children:
            print '%s' % child
            
            for subchild in child.children:
                print '--> %s' % subchild
                
                for subsubchild in subchild.children:
                    print '    --> %s' % subsubchild



if __name__ in ('__main__', '__android__'):
    TouchContinuum().run()
    