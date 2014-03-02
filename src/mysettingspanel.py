'''
IcarusTouch

Copyright (C) 2011  Cyril Stoller

For comments, suggestions or other messages, contact me at:
<cyril.stoller@gmail.com>

This file is part of IcarusTouch.

IcarusTouch is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

IcarusTouch is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with IcarusTouch.  If not, see <http://www.gnu.org/licenses/>.
'''


from glob import glob
from os.path import join, dirname

from kivy.properties import ObjectProperty

from kivy.uix.widget import Widget
from kivy.uix.button import Button


'''
####################################
##
##   MySettingsPanel Class
##
####################################
'''
class MySettingsPanel(Widget):
    background_scroll_view_grid = ObjectProperty(None)
    keyboard_scroll_view_box = ObjectProperty(None)
    is_open = False
    
    def __init__(self, **kwargs):
        super(MySettingsPanel, self).__init__(**kwargs)
        
        # Get the current launch directory
        curdir = dirname(__file__)
        
        '''
        # 
        # I think this isn't working under unix
        # because of the '\\'. Actually, it isn't
        # even working under windows ;-)
        # 
        
        # find all fill-resolution background images
        all_background_images = glob(join(curdir, 'backgrounds/*', 'background_*'))
        all_background_filenames = []
        for image in all_background_images:
            # extract the filname, cut the 'background_' and the file extension
            all_background_filenames.append(image.rpartition('\\')[2])
            all_background_filenames.append(image.replace('background_', '', 1))
            all_background_filenames.append(image.rpartition('.')[0])
        
        all_background_thumbnails = glob(join(curdir, 'backgrounds/*', 'thumbnail_*'))
        all_background_thumbnail_filenames = []
        for background_thumbnail in all_background_thumbnails:
            # extract the filname, cut the 'thumbnail_' and the file extension
            all_background_thumbnail_filenames.append(background_thumbnail.rpartition('\\')[2])
            all_background_thumbnail_filenames.append(background_thumbnail.replace('thumbnail_', '', 1))
            all_background_thumbnail_filenames.append(background_thumbnail.rpartition('.')[0])
        
        print all_background_filenames
        print all_background_thumbnail_filenames
        
        
        all_background_images_and_thumbnails = []
        for background_image_filename in all_background_filenames:   
            # try to find a thumbnail for the image.
            try:
                thumbnail_index = all_background_thumbnail_filenames.index(background_image_filename)
                all_background_images_and_thumbnails.append(all_background_thumbnails[thumbnail_index])
            except Exception, e:
                # means, there isn't a thumbnail for this image.
                all_background_images_and_thumbnails.append(all_background_images[all_background_filenames.index(background_image_filename)])
        '''
        
        # fill the background selector with images
        for filename in glob(join(curdir, 'backgrounds/*', 'background_*')):
            try:
                # load the image
                picture = Button(
                                 background_down=filename,
                                 background_normal=filename,
                                 size_hint_y=None,
                                 height=180
                                 #size=(200, 170)
                                 )
                # add to the grid
                self.background_scroll_view_grid.add_widget(picture)
                
            except Exception, e:
                print 'Background image: Unable to load <%s>. Reason: %s' % (filename, e)
        
        # fill the keyboard selector with images
        for filename in glob(join(curdir, 'keyboards', 'keyboard_*')):
            try:
                # load the image
                picture = Button(
                                 background_down=filename,
                                 background_normal=filename,
                                 size_hint=(None, None),
                                 size=(1250, 195)
                                 )
                # add to the box
                self.keyboard_scroll_view_box.add_widget(picture)
                
            except Exception, e:
                print 'Keyboard image: Unable to load <%s>. Reason: %s' % (filename, e)
