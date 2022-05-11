# Generate plot of DSO image thumbnails on a log distance scale using
# simple rectangle packing layout.
#
# Copyright Kevin Males 2022

from PIL import Image, ImageFont, ImageDraw
from csv import DictReader
from math import log10, ceil
import os.path

########################
# CONFIGURATION SETTINGS
########################

THUMBNAIL_SIZE = 100  # max thumbnail size in pixels
BORDER = 5  # border size around thumbnail and label in pixels
MARGIN = 20  # margin around outside of composite image in pixels (fiducial line labels are drawn in here)
FONT = ImageFont.truetype(font = 'arial.ttf', size = 12)  # font for text labels
LOG_STEP_WIDTH = 500  # width of each logarithmic step along x in pixels

# boundary lines to be drawn on the plot 

BOUNDARIES = {
    'Milky Way': 110000, # distance to far edge of milky way boundary
    'Local Group': 5000000,  # radius of local group
    'Virgo Supercluster': 60000000  # radius of local supercluster
}

IMAGE_FOLDER = 'C:/APT_Images/Processed images'  # top level folder containing image subfolders
IMAGE_DATA = 'Observing & Processing information.csv'  # name of spreadsheet, assumed to be in IMAGE_FOLDER

# mapping from image type column in spreadsheet to image folder under IMAGE_FOLDER

TYPE_MAP = {
    'Star': 'Stars',
    'Cluster': 'Clusters',
    'Galaxy': 'Galaxies',
    'Nebula': 'Nebulae'
}

FILE_INPUT_FORMATS = ['jpg', 'jpeg', 'png']  # look for these file types in this order when loading data
FILE_OUTPUT_FORMATS = ['png', 'pdf']  # output index image in these formats
FILE_SUFFIX = '_crop'  # look for filename with this suffix first, otherwise default to filename as given

BACKGROUND_COLOUR = (255, 255, 255)  # chart background colour
LABEL_COLOUR = (255, 0, 0)  # label colour
SCALE_COLOUR = (0, 0, 250)  # colour of scale lines and text
BOUNDARY_COLOUR = (0, 250, 0)  # colour of boundary marker lines

TARGET_COLNAME = 'Target'  # heading of column containing target name for label
DISTANCE_COLNAME = 'Dist (ly)'  # heading of column containing distance (must be numeric)
TYPE_COLNAME = 'Type'  # heading of column containing type - looked up in TYPE_MAP to find image subfolder
FILENAME_COLNAME = 'Filename'  # heading of column containing target image filename

#####################
# Observation class
#####################

class Observation:
    '''
    Represents an observation. Responsible for rendering image representation
    and calculating layout position
    '''

    def __init__(self, target, pathname, distance):
        # load original image and convert to thumbnail
        image = Image.open(pathname)
        image.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        
        # calculate size of text label
        text_width, text_height = FONT.getsize(target)

        # create new image to encapsulate thumbnail and text label
        lab_im_width = max(image.width, text_width) + 2 * BORDER
        lab_im_height = image.height + text_height + 3 * BORDER

        labelled_image = Image.new('RGB', (lab_im_width, lab_im_height), BACKGROUND_COLOUR)

        # copy thumbnail - note PIL image system has 0,0 in the upper left corner
        image_offset = int(round((lab_im_width - image.width) / 2))
        labelled_image.paste(image, (image_offset, BORDER))

        # render the label text
        d = ImageDraw.Draw(labelled_image)
        text_offset = int(round((lab_im_width - text_width) / 2))
        d.text((text_offset, lab_im_height - BORDER - text_height), target, font = FONT, fill = LABEL_COLOUR)

        # set instance vars for layout calculation
        self.image = labelled_image
        self.width = lab_im_width
        self.height = lab_im_height
        
        # note that layout works y-upwards so y coords need inverting on final render
        self.x = BORDER + int(round(log10(float(distance)) * LOG_STEP_WIDTH))
        self.y = 0

        self.target = target

    def __str__(self):
        return self.target

    # calculate overlap with another observation
    # if there is an overlap return the upper y coord of this observation as this will be
    # the  min y required to clear it

    def bbox(self):
        # x coord is the centre of the image
        half_width = int(self.width / 2)
        return (self.x - half_width, self.y, self.x + half_width, self.y + self.height)

    def overlap(self, obs):
        bbox = self.bbox()
        bbox_obs = obs.bbox()
        if bbox[0] >= bbox_obs[2] or bbox_obs[0] >= bbox[2] or bbox[1] >= bbox_obs[3] or bbox_obs[1] >= bbox[3]:
            return None
        return bbox[3]

    def paste(self, image):
        # need to invert y coordinate which is bottom-up
        image.paste(self.image, (MARGIN + self.x - int(self.width / 2), image.height - MARGIN - self.y - self.height))

#####################
# Folder processing
#####################

def resolve_filename(type, filename):
    if type not in TYPE_MAP:
        return None
    pathname_base = f'{IMAGE_FOLDER}/{TYPE_MAP[type]}/{filename}'
    pathname = None
    # see if there are any files with the suffix and of a valid image type
    for ext in FILE_INPUT_FORMATS:
        p = f'{pathname_base}{FILE_SUFFIX}.{ext}'
        if os.path.exists(p):
            pathname = p
            break
    if pathname is None:
        # Didn't find a suffix file so look for the original filename
        for ext in FILE_INPUT_FORMATS:
            p = f'{pathname_base}.{ext}'
            if os.path.exists(p):
                pathname = p
                break
    return pathname

def draw_labelled_line(d, x, y, h, label, colour):
    d.line([(x, MARGIN), (x, h - MARGIN)], fill = colour)
    l_w, l_h = FONT.getsize(label)
    l_hw = ceil(l_w / 2)
    # clear a rectangle for the text label - ensures label visible over line regardless of font size
    d.rectangle((x - l_hw, y, x + l_hw, y + l_h), fill = BACKGROUND_COLOUR)
    d.text((x - l_hw, y), label, font=FONT, fill = colour)
    # return size of label for offsetting multiple rows of labels
    return l_w, l_h

def process_data():
    observations = []
    placed_observations = []

    with open(f'{IMAGE_FOLDER}/{IMAGE_DATA}', 'r') as f:
        reader = DictReader(f)
        for row in reader:
            target = row[TARGET_COLNAME]
            type = row[TYPE_COLNAME]
            filename = row[FILENAME_COLNAME]
            dist = row[DISTANCE_COLNAME]
            if filename == '':
                # haven't developed this observation yet
                continue
            pathname = resolve_filename(type,filename)
            if pathname is None:
                print(f'Could not find image file for image named {filename} of type {type}')
                continue
            observations.append(Observation(target, pathname, dist))

    # sort observations in descending width order to optimize placement
    # thumbnails are approximately thr same size but text label width can be wider than the thumbnail
    observations.sort(key = lambda x: x.width, reverse = True)

    # step through observations placing them at the lowest available slot
    for obs in observations:
        # observations start with y = 0, calculate overlaps with all placed observations
        overlaps_y = list(filter(None, [o.overlap(obs) for o in placed_observations]))
        # if there are overlaps we need to increase y coord to the max of the overlapping observations
        # once there are no more overlaps this observation is placed
        while len(overlaps_y) > 0:
            obs.y = max(overlaps_y)
            overlaps_y = list(filter(None, [o.overlap(obs) for o in placed_observations]))
        placed_observations.append(obs)

    # now we have everything placed create a master image and copy all observations into it

    bboxes = [o.bbox() for o in observations]
    x_max = max(bboxes, key = lambda bb: bb[2])[2]
    y_max = max(bboxes, key = lambda bb: bb[3])[3]

    # create master image, round up dist scale to next power of 10
    max_power = ceil(x_max / LOG_STEP_WIDTH)
    mi_width = max_power * LOG_STEP_WIDTH + MARGIN * 2

    master_image = Image.new('RGB', (mi_width, y_max + MARGIN * 2), BACKGROUND_COLOUR)

    # draw lines and labels
    d = ImageDraw.Draw(master_image)
    label_height_max = 0
    for i in range(max_power + 1):
        x = MARGIN + i * LOG_STEP_WIDTH
        label = f'10^{str(i)}'
        _, lh = draw_labelled_line(d, x, 0, master_image.height, label, SCALE_COLOUR)
        label_height_max = max(label_height_max, lh)
    
    # draw boundary lines and labels
    for label, dist in BOUNDARIES.items():
        x = MARGIN + int(round(log10(dist) * LOG_STEP_WIDTH))
        draw_labelled_line(d, x, label_height_max, master_image.height, label, BOUNDARY_COLOUR)
        
    for obs in observations:
        obs.paste(master_image)
    
    # write master image to file

    for format in FILE_OUTPUT_FORMATS:
        master_image.save(f'{IMAGE_FOLDER}/index_image.{format}', format)

if __name__ == '__main__':
    process_data()
