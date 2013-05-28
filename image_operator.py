from __future__ import with_statement
import io
import StringIO
from model import Picture
import Image
import imaging
from google.appengine.ext import blobstore
from google.appengine.api import files

class ImageOperator:

    @staticmethod
    def process(owner, content):
        im_data = io.BytesIO(content)
        im_copy = io.BytesIO(content)
        im = Image.open(im_data)
        cf = imaging.ColorFinder(im)
        top = imaging.ColorUtil.generate_color_panes(tuple(cf.strategy_enhanced_complements()))
        output = StringIO.StringIO()
        top.save(output, format="JPEG")
        palette = io.BytesIO(output.getvalue())
        palette_copy = io.BytesIO(output.getvalue())
        output.close()

        upload = Picture(parent=Picture.picture_key(owner))
        upload.owner = owner
        file_name = files.blobstore.create(mime_type='image/jpeg')
        with files.open(file_name, 'a') as f:
            f.write(im_copy.read())
        files.finalize(file_name)
        picture_blob_key = files.blobstore.get_blob_key(file_name)
        upload.picture = str(picture_blob_key)

        palette_name = files.blobstore.create(mime_type='image/jpeg')
        with files.open(palette_name, 'a') as f:
            f.write(palette_copy.read())
        files.finalize(palette_name)
        palette_blob_key = files.blobstore.get_blob_key(palette_name)
        upload.palette = str(palette_blob_key)
        upload.put()

        return palette
