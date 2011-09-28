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


import time

from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.utils import boundary
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.properties import ObjectProperty, NumericProperty

from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.stencilview import StencilView


'''
####################################
##
##   GLOBAL SETTINGS
##
####################################
'''

# Key Graphics
# ---------------------------------------------------------
KEY_FADEOUT_TIME = 0.8
KEY_IMAGE_COLOR = (1, 1, 1, .8)
KEY_IMAGE_COLOR_TRANSPARENT = (1, 1, 1, 0)

UNIVERSAL_KEY_IMAGE = 'images/key_universal.png'
UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN = 0.1
UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MAX = 0.5

# Feedback Wall Graphics
# ---------------------------------------------------------
FEEDBACK_IMAGE_COLOR = (255, 160, 16, 0)
FEEDBACK_IMAGE_TRANSPARENCY_MIN = 0.4
FEEDBACK_IMAGE_TRANSPARENCY_MAX = 1
FEEDBACK_IMAGE_FADEOUT_TIME = 0.4

# Blob Graphics
# ---------------------------------------------------------
#BLOB_IMAGE_FADEOUT_SIZE = BLOB_IMAGE_SIZE * 3 --> hard-wired in the code to 3
BLOB_IMAGE_FADEOUT_TIME = 2.0
BLOB_IMAGE_COLOR = (1, 1, 1, 1)
BLOB_IMAGE_COLOR_TRANSPARENT = (1, 1, 1, 0)

# Rounding Functionality
# ---------------------------------------------------------
KEY_MOVEMENT_THRESHOLD = 1


'''
####################################
##
##   Keyboard Class
##
####################################
'''
class Keyboard(Image):
    keyboard_x_animation = Animation()
    old_keyboard_change_animation = Animation()
    new_keyboard_change_animation = Animation()
    keyboard_is_animated = False
    border_width = NumericProperty(None)
    rounding_function_running = False
    app = ObjectProperty(None)
    key_width = NumericProperty(None)
    
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super(Keyboard, self).on_touch_down(touch)
        
        ud = touch.ud
        
        ######################################################################################################################
        # 
        # Sound actions
        # 
        ######################################################################################################################
        
        # start the rounding algorithm
        if not self.rounding_function_running:
            Clock.schedule_interval(self.roundAllKeys, float(self.parent.app.config.get('Advanced', 'RoundingSchedulerInterval')))
            self.rounding_function_running = True
        
        ud['initial_key'] = self.calculate_key(touch.x)
        ud['finger_position'] = ud['initial_key']['keyposition_relative_to_keyboard']
        ud['rounded_key'] = int(ud['finger_position'] + (self.key_width / 2.0))
        ud['key_moving'] = False
        ud['vibrato'] = False
        
        # (remember that here is the only situation in the code where 'current_position' is set/changed outside the scheduled roundAllKeys function!)
        ud['current_position'] = ud['rounded_key']
        ud['old_position'] = ud['rounded_key']
        
        # set pichbend to neutral middle position
        self.midi_set_pitch_bend(ud)
        
        # Y-Axis to MIDI:
        self.midi_change_y_value(self.bind_y_on_keyboard(touch.y))
        
        # play note
        self.midi_note_on(ud['initial_key']['keynumber'])
        
        ######################################################################################################################
        # 
        # Graphical actions
        # 
        ######################################################################################################################
        
        # this blob stays assigned to the according touch all the time.
        self.create_blob(touch)
        
        # the first key on touch_down is illuminated - all others are illuminated via on_touch_move.
        self.illumniate_key(touch)
        
        # illustrate the current position with a canvas line (if desired)
        if self.parent.app.config.get('Advanced', 'ShowPitchLine') == 'On':
            with self.canvas:
                Color(0, 0, 0)
                ud['canvas_line'] = Rectangle(pos=(ud['current_position']+self.x, self.y), size=(2, self.height))
        
        # Feedback Wall
        # if there is an feedbackwall fadeout animation in progress, stop it.
        self.parent.feedback_wall.feedback_animation.stop(self.parent.feedback_wall)
        self.parent.feedback_wall.transparency = FEEDBACK_IMAGE_TRANSPARENCY_MIN + ((self.bind_y_on_keyboard(touch.y) - self.y) / self.height) * (FEEDBACK_IMAGE_TRANSPARENCY_MAX - FEEDBACK_IMAGE_TRANSPARENCY_MIN)
          
    
    def on_touch_move(self, touch):
        ud = touch.ud
        
        # start the rounding algorithm
        if not self.rounding_function_running:
            Clock.schedule_interval(self.roundAllKeys, float(self.parent.app.config.get('Advanced', 'RoundingSchedulerInterval')))
            self.rounding_function_running = True
        
        # bind all touch coordinates to real keyboard dimensions
        bounded_x = self.bind_x_on_keyboard(touch.x)
        bounded_y = self.bind_y_on_keyboard(touch.y)
        
        bounded_previous_x = self.bind_x_on_keyboard(touch.px)
        bounded_previous_y = self.bind_y_on_keyboard(touch.py)
        
        # here comes all the action for calculating the keyboard position...
        ud['finger_position'] = bounded_x - self.x
        ud['rounded_key'] = int(self.calculate_key(bounded_x)['keyposition_relative_to_keyboard'] + (self.key_width / 2.0))
        #ud['vibrato'] = False
        
        # Y-Axis to MIDI:
        self.midi_change_y_value(bounded_y)
        
        # blob move
        ud['blob'].x = bounded_x - ud['blob'].size[0] / 2
        ud['blob'].y = bounded_y  - ud['blob'].size[1] / 2
        
        # TODO: keypainting with canvas - maybe much bether performance and less ram usage!
        
        # get the key image instances:
        latest_key_stencil = ud['keys'][len(ud['keys'])-1]
        
        # get the position of the key on which the old touch was laying
        oldkeyposition_relative_to_window = self.calculate_key(bounded_previous_x)['keyposition_relative_to_keyboard'] + self.x
        
        # Has the touch moved over a new key?
        if bounded_x < oldkeyposition_relative_to_window or bounded_x > oldkeyposition_relative_to_window + self.key_width - 1:
            
            # maybe the slide was so fast that dx is over self.key_width -> multiple keys where not illuminated cause we "overrun" them.
            '''
            if bounded_previous_x - bounded_x > self.key_width
                # illuminate all keys in beetween this distance. But NOT the newest (that happens later).
                # but don't forget to fade them out right away after creating!
                
                for (bounded_previous_x - bounded_x) / self.key_width # how many keys
                    ?? maybe moving the touch over the expected key, then executing illuminate_key(), then moving etc.?
            '''
            
            # let the old key fade out
            self.key_fadeout(ud['keys'][len(ud['keys'])-1])
            
            # paint new key
            self.illumniate_key(touch)
        
        # nevertheless, the stencil content has to be moved up and down on the key with the touch
        latest_key_stencil.children[1].y += bounded_y - bounded_previous_y
        
        # the universal key has to change its bightness
        latest_key_stencil.children[0].color = (1, 1, 1, UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN + ((bounded_y - self.y) / self.height) * (UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MAX - UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN))
        
        # the feedbackwall has to change his brightness too
        self.parent.feedback_wall.transparency = FEEDBACK_IMAGE_TRANSPARENCY_MIN + ((self.bind_y_on_keyboard(touch.y) - self.y) / self.height) * (FEEDBACK_IMAGE_TRANSPARENCY_MAX - FEEDBACK_IMAGE_TRANSPARENCY_MIN)
    
    
    def on_touch_up(self, touch):
        ud = touch.ud
        
        # MIDI: note off
        self.midi_note_off(ud['initial_key']['keynumber'])
        
        # the pitchbend value should be set to 0 too, but I make this only on touch_down
        # otherwise a sound with some release time (NOT the effects but the sound itself) could be bended around.
        
        # little hack - doesn't know why, but if this isn't here, an initial touch on the bottom of the keyboard gives a short "click" instead of total silence...
        if self.parent.app.config.get('General', 'YAxis') != 'Aftertouch':
            # Y axis = Volume
            self.midi_set_modulation(0)
        
        if 'canvas_line' in ud:
            self.canvas.remove(ud['canvas_line'])
        
        # let the last key fadeout --> only the last has to be faded out by now. the others are already fading
        self.key_fadeout(ud['keys'][len(ud['keys'])-1])
        
        # let the blob fade out
        self.blob_fadeout(touch)
        
        # let the feedback wall disappear
        self.parent.feedback_wall.feedback_animation = Animation(transparency=0, t='out_expo', duration=FEEDBACK_IMAGE_FADEOUT_TIME)
        self.parent.feedback_wall.feedback_animation.start(self.parent.feedback_wall)
    

    '''
    ####################################
    ##
    ##   Graphical Functions
    ##
    ####################################
    '''
    def create_blob(self, touch):
        ud = touch.ud
        
        ud['blob'] = Image(
            source=self.parent.app.config.get('Advanced', 'BlobImage'),
            color=BLOB_IMAGE_COLOR,
            allow_stretch=True,
            size=(self.parent.app.config.getint('Advanced', 'BlobSize'), self.parent.app.config.getint('Advanced', 'BlobSize')))
        
        ud['blob'].x = touch.x - ud['blob'].size[0] / 2
        ud['blob'].y = touch.y - ud['blob'].size[1] / 2
        self.add_widget(ud['blob'])
    
    def illumniate_key(self, touch):
        ud = touch.ud
        
        bounded_x = self.bind_x_on_keyboard(touch.x)
        bounded_y = self.bind_y_on_keyboard(touch.y)
        
        # port the whole calculation shit into "calculate_key"
        # find on which x position to put the key
        x_to_keyboard = bounded_x - self.x;
        y_to_keyboard = bounded_y - self.y;
        keynumber_absolute = int(x_to_keyboard / self.key_width);
        keyposition_to_keyboard = keynumber_absolute * self.key_width;
        keyposition_absolute_x = keyposition_to_keyboard + self.x;
        keyposition_absolute_y = y_to_keyboard + self.y - 500;
        
        
        stencil = StencilView(
            size=(self.key_width-2, self.height-2),
            pos=(keyposition_absolute_x+1, self.y+1))
        
        stencil.add_widget(Image(
            color=KEY_IMAGE_COLOR,
            source=self.parent.app.config.get('Advanced', 'KeyImage'),
            allow_stretch=True,
            size=(100, 1000),
            pos=(keyposition_absolute_x-25, keyposition_absolute_y)))
        
        stencil.add_widget(Image(
            color=(1, 1, 1, UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN + (y_to_keyboard / self.height) * (UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MAX - UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN)),
            source=UNIVERSAL_KEY_IMAGE,
            allow_stretch=True,
            size=(100, 500),
            pos=(keyposition_absolute_x, self.y)))
        
        # if the key 'keys' wasn't created yet, create it now.
        if not 'keys' in ud:
            ud['keys'] = [Widget()]
        
        # then add the key to the list of this touch AND to the root widget
        ud['keys'].append(stencil)
        self.add_widget(stencil)
        
        # workarround for having the blob image IN FRONT of the key images
        self.remove_widget(ud['blob'])
        self.add_widget(ud['blob'])
    
    
    def key_fadeout(self, stencil):
        animation = Animation(color=KEY_IMAGE_COLOR_TRANSPARENT, t='out_expo', duration=KEY_FADEOUT_TIME)
        animation2 = Animation(color=(1, 1, 1, 0), t='out_expo', duration=KEY_FADEOUT_TIME)
        
        animation.start(stencil.children[0])
        animation2.start(stencil.children[1])
        
        animation.bind(on_complete=self.key_fadeout_complete)
        animation2.bind(on_complete=self.key_fadeout_complete)
    
    
    def blob_fadeout(self, touch):
        ud = touch.ud
        fadeoutpos = ud['blob'].pos
        
        animation = Animation(
            color=BLOB_IMAGE_COLOR_TRANSPARENT,
            size=(self.parent.app.config.getint('Advanced', 'BlobSize') * 3, self.parent.app.config.getint('Advanced', 'BlobSize') * 3),
            x=fadeoutpos[0] - self.parent.app.config.getint('Advanced', 'BlobSize'), # workarround for centering the image during resizing
            y=fadeoutpos[1] - self.parent.app.config.getint('Advanced', 'BlobSize'), # workarround for centering the image during resizing
            t='out_expo', duration=BLOB_IMAGE_FADEOUT_TIME)
        
        animation.start(ud['blob'])
        animation.bind(on_complete=self.blob_fadeout_complete)
    
    
    def blob_fadeout_complete(self, animation, widget):
        self.remove_widget(widget)
    
    
    def key_fadeout_complete(self, animation, widget):
        # first look up if the other key image has already been deleted (in his own instance of this method)
        if len(widget.parent.children) == 1:
            
            # if so, delete the whole parent widget (Stencil)!
            self.remove_widget(widget.parent)
            
        else:
            
            #if not, delete only the actual calling key image.
            widget.parent.remove_widget(widget)
    
    
    '''
    ####################################
    ##
    ##   Calculating Functions
    ##
    ####################################
    '''
    def bind_x_on_keyboard(self, x):
        win = self.get_parent_window()
        bounded_x = x
        if self.x > 0: # if on the left side of the keyboard
            bounded_x = boundary(x, self.x, win.width)
        
        elif self.x < win.width - self.width: # if on the right side of the keyboard
            bounded_x = boundary(x, 0, self.x + self.width)
        return bounded_x
    
    
    def bind_y_on_keyboard(self, y):
        bounded_y = boundary(y, self.y, self.top)
        return bounded_y
    
    
    def calculate_key(self, x):
        bounded_x = self.bind_x_on_keyboard(x)
        x_relative_to_keyboard = bounded_x - self.x;
        
        keynumber = int(x_relative_to_keyboard / self.key_width);
        keyposition_relative_to_keyboard = keynumber * self.key_width;
        
        returnvalue = {'keyposition_relative_to_keyboard': keyposition_relative_to_keyboard, 'keynumber': keynumber,}        
        return returnvalue
    
    def roundAllKeys(self, dt):
        request_scheduler_continue = False
        
        # do the rounding for all existing touches simultanous
        for touch in EventLoop.touches[:]:
            ud = touch.ud
            
            if 'initial_key' in ud:
                
                if self.parent.app.config.get('General', 'PitchLock') == 'On':
                    # Fully rounding - chromatic
                    ud['current_position'] = ud['rounded_key']
                    request_scheduler_continue = False
                    
                else:
                    # this is the actual "rounding algorithm"...
                    ud['key_moving'] = time.time() - touch.time_update < float(self.parent.app.config.get('Advanced', 'MovementDecay')) and abs(touch.dx) > KEY_MOVEMENT_THRESHOLD
                    
                    if ud['key_moving']:
                        ud['current_position'] = ud['old_position'] + (ud['finger_position'] - ud['old_position']) * float(self.parent.app.config.get('Advanced', 'RoundSpeedToFinger'))
                    else:
                        ud['current_position'] = ud['old_position'] + (ud['rounded_key'] - ud['old_position']) * float(self.parent.app.config.get('Advanced', 'RoundSpeedToKey'))
                        # prevent from changes under 1 pixel, that doesn't makes sense and keeps the scheduler running -> bad performance
                        if abs(ud['rounded_key'] - ud['current_position']) <= 1:
                            ud['current_position'] = ud['rounded_key']
                
                # if the rounding is not yet completely done, require more callbacks
                # that means when all the touches will have new == old, the callback will return false, the scheduler will stop.
                if int(ud['current_position']) != int(ud['old_position']) or int(ud['current_position']) != ud['rounded_key']:
                    request_scheduler_continue = True
                
                # if there is still any change on the position, keep on sending MIDI pitch data:
                self.midi_set_pitch_bend(ud)
                
                # rounding algorithm debugging:
                #print '%i,%i,%i,%i,%i' % (ud['old_position'], ud['finger_position'], ud['key_moving'], ud['rounded_key'], ud['current_position'])
                
                if 'canvas_line' in ud:
                    ud['canvas_line'].pos = int(ud['current_position']) + self.x, self.y
                
                # store history data
                ud['old_position'] = ud['current_position']
        # if the function is not used anymore, stop the scheduler
        self.rounding_function_running = request_scheduler_continue
        return request_scheduler_continue
        
        self.rounding_function_running = True
        return True
    
    
    '''
    ####################################
    ##
    ##   MIDI Functions
    ##
    ####################################
    '''
    def midi_note_on(self, note):  
        '''
        # I don't know if this is working properly...      
        if self.parent.app.config.get('MIDI', 'VoiceMode') == 'Monophonic'
            # kill all existing notes
            for search_touch in EventLoop.touches[:]:
                if 'initial_key' in search_touch.ud and search_touch.ud['initial_key']['keynumber]' != note:
                    self.parent.midi_out.note_off(search_touch.ud['initial_key']['keynumber]' + self.parent.app.config.getint('MIDI', 'Transpose'), 0, 0)
        '''
        self.parent.midi_out.note_on(note + self.parent.app.config.getint('MIDI', 'Transpose'), 127, self.parent.app.config.getint('MIDI', 'Channel'))
    
    
    def midi_note_off(self, note): # midi_note_off(self, note , touch):
        '''
        # I don't know if this is working properly...  
        if self.parent.app.config.get('MIDI', 'VoiceMode') == 'Monophonic'
            # if the voice mode is set to mono, and the latest key is removed, see if there is yet another key touched - this would then be turned on again.
            for search_touch in EventLoop.touches[:]:
                if 'initial_key' in search_touch.ud and search_touch.ud['initial_key']['keynumber]' != note:
                    # there is another key touched. If he was touched earlier than the current one, turn him on ( i hope he was turned of before...)
                    other_touches.append(search_touch)
            
            for other_touch in other_touches:
                if other_touch.time_start < touch.time_start:
                    # TODO: there could be several other touches - pick the "youngest" one.
                    self.midi_note_on(other_touch.ud['initial_key']['keynumber]')
        '''
        self.parent.midi_out.note_off(note + self.parent.app.config.getint('MIDI', 'Transpose'), 0, 0)
    
    
    def midi_change_y_value(self, y):
        calculated_y = int(127 * ((y - self.y) / self.height))
        if self.parent.app.config.get('General', 'YAxis') == 'Aftertouch':
            # Y axis = Aftertouch
            self.midi_set_aftertouch(calculated_y)
        else:
            # Y axis = Volume
            self.midi_set_modulation(calculated_y)
    
    
    def midi_set_aftertouch(self, y):
        self.parent.midi_out.write_short(0xD0 + self.parent.app.config.getint('MIDI', 'Channel'), y)
    
    
    def midi_set_modulation(self, y):
        self.parent.midi_out.write_short(0xB0 + self.parent.app.config.getint('MIDI', 'Channel'), self.parent.app.config.getint('MIDI', 'CCController'), y)
    
    
    def midi_set_pitch_bend(self, ud):
        # Now, the ud['current_position'] has to be converted to a MIDI pitch bend value and sent over MIDI
        pixel_distance = int(ud['current_position']) - (ud['initial_key']['keyposition_relative_to_keyboard'] + (self.key_width / 2.0))
        # pitch-resolution: (+/-) = 2^14 / 2 = 8192
        # pitch-range: (+/-) = 2 Oct = 24 semitones (NM G2X)
        # pitch values per semitone: 8192 / 48 = 170.6667
        # pixel per semitone: 50
        # pitch values per pixel: 170.6667 / 50 = 3.41333  = 8192 / (24 * 50)
        pitch_value = int(pixel_distance * 8192.0 / (self.parent.app.config.getint('MIDI', 'PitchBendRange') * self.key_width) + 0.5) + 8192 # (center/normal = 8192)
        
        self.parent.midi_out.write_short(0xE0 + self.parent.app.config.getint('MIDI', 'Channel'), pitch_value - int(pitch_value / 128) * 128, int(pitch_value / 128))
