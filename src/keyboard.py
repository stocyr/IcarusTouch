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
        # if the touch doesn't belong to me, discard it
        if not self.collide_point(*touch.pos):
            return super(Keyboard, self).on_touch_down(touch)
        
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        ######################################################################################################################
        # 
        # Sound actions
        # 
        ######################################################################################################################
        
        # if not yet started, start the rounding algorithm now
        if not self.rounding_function_running:
            Clock.schedule_interval(self.roundAllKeys, float(self.parent.app.config.get('Advanced', 'RoundingSchedulerInterval')))
            self.rounding_function_running = True
        
        # define all the touch-specific properties with the given key touched
        ud['initial_key'] = self.calculate_key(touch.x)
        ud['finger_position'] = ud['initial_key']['keyposition_relative_to_keyboard']
        ud['rounded_key'] = int(ud['finger_position'] + (self.key_width / 2.0))
        ud['key_moving'] = False
        ud['vibrato'] = False # this isn't implemented yet.
        
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
        
        # feedback wall: if there is an feedbackwall fadeout animation in progress, stop it.
        self.parent.feedback_wall.feedback_animation.stop(self.parent.feedback_wall)
        self.parent.feedback_wall.transparency = FEEDBACK_IMAGE_TRANSPARENCY_MIN + ((self.bind_y_on_keyboard(touch.y) - self.y) / self.height) * (FEEDBACK_IMAGE_TRANSPARENCY_MAX - FEEDBACK_IMAGE_TRANSPARENCY_MIN)
          
    
    def on_touch_move(self, touch):
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        # if not yet started, start the rounding algorithm
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
        
        # TODO: key painting with canvas - maybe much better performance and less ram usage!
        
        # get the key image instance: I just have to modify the latest key in the entire list (which is the one I'm currently touching):
        latest_key_stencil = ud['keys'][len(ud['keys'])-1]
        
        # get the position of the key on which the old touch was laying
        oldkeyposition_relative_to_window = self.calculate_key(bounded_previous_x)['keyposition_relative_to_keyboard'] + self.x
        
        # Has the touch moved over a new key?
        if bounded_x < oldkeyposition_relative_to_window or bounded_x > oldkeyposition_relative_to_window + self.key_width - 1:
            
            # maybe the slide was so fast that touch.dx is over self.key_width -> multiple keys where not illuminated cause we "overrun" them.
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
        
        # regardless of the x-movement, the stencil's "key image" has to be moved up and down on the key with the touch's y-position
        # (because the key image lays over the universal key image (it is on the top) its index is the lower one = 0)
        latest_key_stencil.children[0].y += bounded_y - bounded_previous_y
        
        # the universal key has to change its brightness
        # (because the universal key image lays under the key image (it is on the bottom) its index is the higher one = 1)
        latest_key_stencil.children[1].color = (1, 1, 1, UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN + ((bounded_y - self.y) / self.height) * (UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MAX - UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN))
        
        # the feedback wall has to change its brightness too
        self.parent.feedback_wall.transparency = FEEDBACK_IMAGE_TRANSPARENCY_MIN + ((self.bind_y_on_keyboard(touch.y) - self.y) / self.height) * (FEEDBACK_IMAGE_TRANSPARENCY_MAX - FEEDBACK_IMAGE_TRANSPARENCY_MIN)
    
    
    def on_touch_up(self, touch):
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        # MIDI: note off
        self.midi_note_off(ud['initial_key']['keynumber'])
        
        # the pitchbend value should be set to 0 too, but I make this not until a new touch_down occurs,
        # otherwise a sound with some release time (NOT the effects but the sound itself) could be bended around.
        
        # little hack - don't know why, but if this isn't here, an initial touch on the bottom of the keyboard gives a short "click" instead of total silence...
        if self.parent.app.config.get('General', 'YAxis') != 'Aftertouch':
            # Y axis = Volume
            self.midi_set_modulation(0)
        
        # if the advanced setting "pitch line" was turned on, delete the line by now.
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
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        # create the new blob
        ud['blob'] = Image(
            source=self.parent.app.config.get('Advanced', 'BlobImage'),
            color=BLOB_IMAGE_COLOR,
            allow_stretch=True,
            size=(self.parent.app.config.getint('Advanced', 'BlobSize'), self.parent.app.config.getint('Advanced', 'BlobSize')))
        
        # set the blobs position right under the finger
        ud['blob'].x = touch.x - ud['blob'].size[0] / 2
        ud['blob'].y = touch.y - ud['blob'].size[1] / 2
        self.add_widget(ud['blob'])
    
    def illumniate_key(self, touch):
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        # bind all touch coordinates to real keyboard dimensions
        bounded_x = self.bind_x_on_keyboard(touch.x)
        bounded_y = self.bind_y_on_keyboard(touch.y)
        
        # TODO: port the whole calculation into "calculate_key"
        # find out on which x position to put the key
        x_to_keyboard = bounded_x - self.x;
        y_to_keyboard = bounded_y - self.y;
        keynumber_absolute = int(x_to_keyboard / self.key_width);
        keyposition_to_keyboard = keynumber_absolute * self.key_width;
        keyposition_absolute_x = keyposition_to_keyboard + self.x;
        keyposition_absolute_y = y_to_keyboard + self.y - 500;
        
        # create a stencilView with the dimension of one key
        stencil = StencilView(
            size=(self.key_width-2, self.height-2),
            pos=(keyposition_absolute_x+1, self.y+1))
        
        # first, add an image called "universal key" which is just a white image. This can be made more or less bright (changes with the y-position of the finger)
        stencil.add_widget(Image(
            color=(1, 1, 1, UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN + (y_to_keyboard / self.height) * (UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MAX - UNIVERSAL_KEY_IMAGE_TRANSPARENCY_MIN)),
            source=UNIVERSAL_KEY_IMAGE,
            allow_stretch=True,
            size=(100, 500),
            pos=(keyposition_absolute_x, self.y)))
        
        # then, add an image called "key image" which is basically a huge blob in a rectangle shape. It changes his position with the y-position of the finger
        stencil.add_widget(Image(
            color=KEY_IMAGE_COLOR,
            source=self.parent.app.config.get('Advanced', 'KeyImage'),
            allow_stretch=True,
            size=(100, 1000),
            pos=(keyposition_absolute_x-25, keyposition_absolute_y)))
        
        # if the user dictionary key 'keys' wasn't created yet, create it now.
        if not 'keys' in ud:
            ud['keys'] = [Widget()]
        
        # then add the key to the list of this touch AND to the keybaord widget
        ud['keys'].append(stencil)
        self.add_widget(stencil)
        
        # workaround for having the blob image IN FRONT of the key images
        self.remove_widget(ud['blob'])
        self.add_widget(ud['blob'])
    
    
    def key_fadeout(self, stencil):
        # make the key fade out
        animation = Animation(color=KEY_IMAGE_COLOR_TRANSPARENT, t='out_expo', duration=KEY_FADEOUT_TIME)
        animation2 = Animation(color=(1, 1, 1, 0), t='out_expo', duration=KEY_FADEOUT_TIME)
        
        animation.start(stencil.children[0])
        animation2.start(stencil.children[1])
        
        # after fading out, call the "death"-function
        animation.bind(on_complete=self.key_fadeout_complete)
        animation2.bind(on_complete=self.key_fadeout_complete)
    
    
    def blob_fadeout(self, touch):
        # define a short name for the touch-specific and unique UserDictionary "ud"
        ud = touch.ud
        
        fadeoutpos = ud['blob'].pos
        
        # make the blob fade out
        animation = Animation(
            color=BLOB_IMAGE_COLOR_TRANSPARENT,
            size=(self.parent.app.config.getint('Advanced', 'BlobSize') * 3, self.parent.app.config.getint('Advanced', 'BlobSize') * 3),
            x=fadeoutpos[0] - self.parent.app.config.getint('Advanced', 'BlobSize'), # workarround for centering the image during resizing
            y=fadeoutpos[1] - self.parent.app.config.getint('Advanced', 'BlobSize'), # workarround for centering the image during resizing
            t='out_expo', duration=BLOB_IMAGE_FADEOUT_TIME)
        
        animation.start(ud['blob'])
        
        # after fading out, call the "death"-function
        animation.bind(on_complete=self.blob_fadeout_complete)
    
    
    def blob_fadeout_complete(self, animation, widget):
        self.remove_widget(widget)
    
    
    def key_fadeout_complete(self, animation, widget):
        # first look up if the other key image has already been deleted (in his own call of this method)
        if len(widget.parent.children) == 1:
            # if so, delete the whole parent widget (= a StencilView)!
            self.remove_widget(widget.parent)
            
        else:
            #if not, delete only the actual calling key image. The other key will do the rest.
            widget.parent.remove_widget(widget)
    
    
    '''
    ####################################
    ##
    ##   Calculating Functions
    ##
    ####################################
    '''
    def bind_x_on_keyboard(self, x):
        # bind the fingers position to a real possible keyboard location.
        # get the parent window to look up the screen size.
        win = self.get_parent_window()
        bounded_x = x
        
        # if on the left side of the keyboard
        if self.x > 0:
            bounded_x = boundary(x, self.x, win.width)
        
        # if on the right side of the keyboard
        elif self.x < win.width - self.width:
            bounded_x = boundary(x, 0, self.x + self.width)
        
        return bounded_x
    
    
    def bind_y_on_keyboard(self, y):
        # bind the fingers position to a real possible keyboard location
        bounded_y = boundary(y, self.y, self.top)
        return bounded_y
    
    
    def calculate_key(self, x):
        # calculate useful informations concerning the key pressed, this keys absolute and relative position and so on.
        bounded_x = self.bind_x_on_keyboard(x)
        x_relative_to_keyboard = bounded_x - self.x;
        
        keynumber = int(x_relative_to_keyboard / self.key_width);
        keyposition_relative_to_keyboard = keynumber * self.key_width;
        
        returnvalue = {'keyposition_relative_to_keyboard': keyposition_relative_to_keyboard, 'keynumber': keynumber,}        
        return returnvalue
    
    def roundAllKeys(self, dt):
        # main function to rounding the pitch AND main function for sending pitch informations over MIDI!
        
        request_scheduler_continue = False
        
        # do the rounding simultanous for all existing touches
        for touch in EventLoop.touches[:]:
            # define a short name for the touch-specific and unique UserDictionary "ud"
            ud = touch.ud
            
            # if this is not a touch on the keyboard,
            if not 'initial_key' in ud:
                # don't handle it at all.
                continue
            
            # if there is no "rounding" but only hard lock to chromatic keys:
            if self.parent.app.config.get('General', 'PitchLock') == 'On':
                # Fully rounding - chromatic
                ud['current_position'] = ud['rounded_key']
                request_scheduler_continue = False
            else:
                # this is the actual "rounding algorithm"...
                ud['key_moving'] = time.time() - touch.time_update < float(self.parent.app.config.get('Advanced', 'MovementDecay')) and abs(touch.dx) > KEY_MOVEMENT_THRESHOLD
                
                if ud['key_moving']:
                    # if the finger is moving around, snap to the finger.
                    ud['current_position'] = ud['old_position'] + (ud['finger_position'] - ud['old_position']) * float(self.parent.app.config.get('Advanced', 'RoundSpeedToFinger'))
                else:
                    # if the finger stands still, snap to the key under it --> ROUND.
                    ud['current_position'] = ud['old_position'] + (ud['rounded_key'] - ud['old_position']) * float(self.parent.app.config.get('Advanced', 'RoundSpeedToKey'))
                    # prevent from changes under 1 pixel, that doesn't makes sense and keeps the scheduler running -> bad performance
                    if abs(ud['rounded_key'] - ud['current_position']) <= 1:
                        ud['current_position'] = ud['rounded_key']
            
            # if the rounding is not yet completely done, require more callbacks.
            # that means when all the touches in the for...in-loop will have new == old, the callback will return false, the scheduler will stop.
            if int(ud['current_position']) != int(ud['old_position']) or int(ud['current_position']) != ud['rounded_key']:
                request_scheduler_continue = True
            
            # tha fact that I am here prooves that there is still a change on the position, so keep on sending MIDI pitch data:
            self.midi_set_pitch_bend(ud)
            
            # rounding algorithm debugging:
            #print '%i,%i,%i,%i,%i' % (ud['old_position'], ud['finger_position'], ud['key_moving'], ud['rounded_key'], ud['current_position'])
            
            # if the advanced setting "pitch line" is turned on, move it with the pitch
            if 'canvas_line' in ud:
                ud['canvas_line'].pos = int(ud['current_position']) + self.x, self.y
            
            # store history data
            ud['old_position'] = ud['current_position']
            
        # if the function is not used anymore, stop the scheduler
        self.rounding_function_running = request_scheduler_continue
        return request_scheduler_continue
    
    
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
        # relative y-axis-value (from 0 - 127)
        calculated_y = int(127 * ((y - self.y) / self.height))
        
        # look up what MIDI value to change with the y-axis
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
