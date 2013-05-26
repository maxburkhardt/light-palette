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
    def __init__(self, data=None):
        if data == None:
            self.data = []
        else:
            self.data = data
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
    def remove(self, value):
        for i in range(len(self.data)):
            if self.data[i][1] == value:
                del self.data[i]
                return
    def pop(self):
        return self.data.pop(0)
    def pm_copy(self):
        return PriorityMap(list(self.data))


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


class ColorUtil:
    @staticmethod
    def convert_to_hsv(color):
        return colorsys.rgb_to_hsv(color[0]/256.0, color[1]/256.0, color[2]/256.0)

    @staticmethod
    def convert_to_rgb(color):
        reverted = colorsys.hsv_to_rgb(color[0], color[1], color[2])
        return (int(reverted[0] * 256), int(reverted[1] * 256), int(reverted[2] * 256))

    @staticmethod
    def map_to_hsv(colormap):
        priori = PriorityMap()
        for item in colormap.data:
            priori.add(item[0], ColorUtil.convert_to_hsv(tuple(item[1])))
        return priori

    @staticmethod
    def display_color(colors, size=(100, 100)):
        display = Image.new("RGB", size)
        display_pixmap = display.load()
        for x in range(100):
            for y in range(100):
                display_pixmap[x, y] = colors
        display.show()
    
    @staticmethod
    def generate_color_panes(colors, size=(640, 360)):
        display = Image.new("RGB", size)
        display_pixmap = display.load()
        num_colors = len(colors)
        bar_width = int(size[0] / num_colors)
        for i in range(num_colors):
            for x in range((i * bar_width), ((i+1) * bar_width)):
                for y in range(size[1]):
                    display_pixmap[x, y] = colors[i]
        return display

    # Given two HSV colors, find their difference in hues
    @staticmethod
    def find_hue_difference(color1, color2):
        greater = max(color1, color2)
        smaller = min(color1, color2)
        diff = greater - smaller
        return min(diff, 1-diff)

# Class to do the magic
# Takes a PIL Image object
class ColorFinder:

    def __init__(self, image):
        stat = ImageStat.Stat(im)
        self.pixel_count = stat.count[0]
        self.computation = self.compute_pop_map(image)
        self.conversion = ColorUtil.map_to_hsv(self.computation)

    # Currently does every third pixel, for speed
    def compute_pop_map(self, image):
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

    # generic function to find something that is both <quality> and popular
    # quality should be a lambda that takes a color and outputs a value between 0 and 1
    # 1 being the best, 0 being the worst
    # example to find something bright & popular:
    # find_quality_popular(colormap, lambda x: x[1][2])
    # example to find something close & popular:
    # find_quality_popular(colormap, lambda x: 1- ColorUtil.find_hue_difference(target_hue, x[1][0])
    def find_quality_popular(self, quality, colormap=None, qual_weight=0.5, pop_weight=0.5):
        if colormap == None:
            colormap = self.conversion
        best_so_far = (0, None)
        for color in colormap.data:
            qual_score = quality(color)
            pop_score = color[0] / self.pixel_count
            total_score = (qual_score * qual_weight) + (pop_score * pop_weight)
            if total_score > best_so_far[0]:
                best_so_far = (total_score, color[1])
        return best_so_far[1]

    # finds the top colors in the colormap
    def strategy_top_colors(self, count, colormap=None):
        if colormap == None:
            colormap = self.computation
        returnable = []
        for i in range(count):
            returnable.append(tuple(colormap.data[i][1]))
        return returnable

    def strategy_enhanced_triad(self, colormap=None):
        if colormap == None:
            colormap = self.conversion
        copied = colormap.pm_copy()
        cp_color = self.find_quality_popular(ColorQualities.colorful())

        pal = Palette()
        idealscheme = pal.produce_colors(cp_color, "TRIAD")
        colorscheme = []
        
        for color in idealscheme:
            match = self.find_quality_popular(ColorQualities.close(color[0]), colormap=copied)
            copied.remove(match)
            colorscheme.append(ColorUtil.convert_to_rgb(match))
                
        if cp_color[2] > 0.7:
            colorscheme.append(ColorUtil.convert_to_rgb(self.find_quality_popular(ColorQualities.dark(), colormap=copied)))
        else:
            colorscheme.append(ColorUtil.convert_to_rgb(self.find_quality_popular(ColorQualities.bright(), colormap=copied)))
        return colorscheme

# returns lambdas to be used with ColorFinder.find_quality_popular
class ColorQualities:

    @staticmethod
    def colorful():
        return lambda x: x[1][1]

    @staticmethod
    def bright():
        return lambda x: x[1][2]

    @staticmethod
    def dark():
        return lambda x: 1 - x[1][2]

    @staticmethod
    def close(target):
        return lambda x: 1- ColorUtil.find_hue_difference(target, x[1][0])

if __name__ == "__main__":
    path = sys.argv[1]
    im = Image.open(path)
    cf = ColorFinder(im)
    top = ColorUtil.generate_color_panes(tuple(cf.strategy_top_colors(4)))
    top.show()
    et = ColorUtil.generate_color_panes(tuple(cf.strategy_enhanced_triad()))
    et.show()
