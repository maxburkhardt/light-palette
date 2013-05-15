#!/usr/bin/env python
import Image
import ImageStat
import colorsys
import sys
import math

# Class to keep track of data with an arbitrary value attached to it
# Provide a value and some data to the add function, and the item will be inserted in to the structure
# Structure is always kept in order according to the first value in each tuple
class PriorityMap:
    def __init__(self):
        self.data = []
    def __str__(self):
        return str(self.data)
    def add(self, value, item):
        inserted = False
        for i in range(len(self.data)):
            if self.data[0][0] < value:
                self.data.insert(i, (value, item))
                inserted = True
        if inserted == False:
            self.data.append((value, item))
    def pop(self):
        return self.data.pop(0)


# Class to keep track of buckets of colors
# Each bucket covers 8x8x8 colors, for a total of 512 colors per bucket
class PopMap:
    def __init__(self):
        self.buckets = {}
        i = 0
        while i < 256:
            self.buckets[i] = {}
            j = 0
            while j < 256:
                self.buckets[i][j] = {}
                k = 0
                while k < 256:
                    self.buckets[i][j][k] = []
                    k = k + 8
                j = j + 8
            i = i + 8
    def add(self, colors):
        bucket = []
        for color in colors:
            nearby = math.floor(color/8.0)
            bucket.append(int(nearby - (nearby % 8)))
        self.buckets[bucket[0]][bucket[1]][bucket[2]].append(colors)
    # Return a Priority Map of (number of pixels in bucket, average color in bucket)
    def compute(self):
        returnable = PriorityMap()
        for rvalue, green in self.buckets.iteritems():
            for gvalue, blue in self.buckets[rvalue].iteritems():
                for bvalue, pixels in self.buckets[rvalue][gvalue].iteritems():
                    count = len(pixels)
                    totals = [0, 0, 0]
                    if count == 0:
                        continue
                    for pixel in pixels:
                        totals[0] += pixel[0]
                        totals[1] += pixel[1]
                        totals[2] += pixel[2]
                    for i in range(3):
                        totals[i] = int(totals[i] / count)
                    returnable.add(count, totals)
        return returnable

# Class of color transformations
# Given a single color, find other ones that look good with it, according to a set of schemes
class Palette:
    MONO = [0]
    COMPLEMENT = [0, 0.5]
    TRIAD = [0, 0.4166666666666667, 0.5833333333333334]
    TETRAD = [0, 0.08333333333333333, 0.5, 0.5833333333333334]
    ACC_ANALOG = [0, 0.08333333333333333, 0.5, 0.9166666666666666]

    # given an HSV color, give other colors that would work well
    def produce_colors(self, color, intended_scheme):
        scheme = None
        if intended_scheme == "MONO":
            scheme = Palette.MONO
        elif intended_scheme == "COMPLEMENT":
            scheme = Palette.COMPLEMENT
        elif intended_scheme == "TRIAD":
            scheme = Palette.TRIAD
        elif intended_scheme == "TETRAD":
            scheme = Palette.TETRAD
        elif intended_scheme == "ACC_ANALOG":
            scheme = Palette.ACC_ANALOG 
        result = []
        for element in scheme:
            result.append([(color[0] + element) % 1, color[1], color[2]]) 
        return result

def display_color(colors, size=100):
    display = Image.new("RGB", (size, size))
    display_pixmap = display.load()
    for x in range(100):
        for y in range(100):
            display_pixmap[x, y] = colors
    display.show()

# Currently does every third pixel, for speed
def compute_pop_map(image):
    pop = PopMap()
    pixmap = image.load()
    width = image.size[0]
    height = image.size[1]
    x = 0
    while x < width - (width % 3):
        y = 0
        while y < height - (height % 3):
            pop.add(pixmap[x,y])
            y += 3
        x += 3
    return pop.compute()

def convert_to_hsv(color):
    return colorsys.rgb_to_hsv(color[0]/256.0, color[1]/256.0, color[2]/256.0)

def convert_to_rgb(color):
    reverted = colorsys.hsv_to_rgb(color[0], color[1], color[2])
    return (int(reverted[0] * 256), int(reverted[1] * 256), int(reverted[2] * 256))

def map_to_hsv(colormap):
    priori = PriorityMap()
    for item in colormap.data:
        priori.add(item[0], convert_to_hsv(tuple(item[1])))
    return priori

# Given two HSV colors, find their difference in hues
def find_hue_difference(color1, color2):
    greater = max(color1, color2)
    smaller = min(color1, color2)
    diff = greater - smaller
    return min(diff, 1-diff)

# Given a PriorityMap of HSV colors, find one that is both bright and popular
def find_colorful_popular(colormap, total_pixels, bright_weight=0.5, pop_weight=0.5):
    best_so_far = (0, None)
    for color in colormap.data:
        bright_score = color[1][1]
        pop_score = color[0] / total_pixels
        total_score = (bright_score * bright_weight) + (pop_score * pop_weight)
        if total_score > best_so_far[0]:
            best_so_far = (total_score, color[1])
    return best_so_far[1]

# Given a PriorityMap of HSV colors and a target hue, find one that is both close and popular
def find_close_popular(colormap, total_pixels, target_hue, close_weight=0.5, pop_weight=0.5):
    best_so_far = (0, None)
    for color in colormap.data:
        close_score = 1 - find_hue_difference(target_hue, color[1][0])
        pop_score = color[0] / total_pixels
        total_score = (close_score * close_weight) + (pop_score * pop_weight)
        if total_score > best_so_far[0]:
            best_so_far = (total_score, color[1])
    return best_so_far[1]

def display_top_colors(count, colormap):
    for i in range(count):
        display_color(tuple(colormap.data[i][1]))


# open up the image
path = sys.argv[1]
im = Image.open(path)
stat = ImageStat.Stat(im)

# find bucketed colors, in order of popularity
computation = compute_pop_map(im)
print computation
conversion = map_to_hsv(computation)
print conversion
cp_color = find_colorful_popular(conversion, stat.count[0])

pal = Palette()
colorscheme = pal.produce_colors(cp_color, "ACC_ANALOG")

for color in colorscheme:
    display_color(convert_to_rgb(find_close_popular(conversion, stat.count[0], color[0])))
