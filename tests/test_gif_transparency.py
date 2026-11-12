# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from io import BytesIO
from unittest import TestCase

from PIL import Image

from thumbor.config import Config
from thumbor.context import Context
from thumbor.engines.pil import Engine


def make_palette_gif_with_transparent_background():
    # Left half is fully transparent, right half is solid blue.
    source = Image.new("RGBA", (80, 50), (0, 0, 0, 0))
    for x in range(40, 80):
        for y in range(50):
            source.putpixel((x, y), (0, 0, 255, 255))
    palette_image = source.convert("P", palette=Image.Palette.ADAPTIVE)
    transparent_index = palette_image.getpixel((0, 0))
    buffer = BytesIO()
    palette_image.save(buffer, "GIF", transparency=transparent_index)
    return buffer.getvalue()


class GifTransparencyTestCase(TestCase):
    def get_context(self):
        cfg = Config(SECURITY_KEY="ACME-SEC", ENGINE="thumbor.engines.pil")
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.STORAGE = "thumbor.storages.no_storage"
        cfg.PILLOW_PRESERVE_INDEXED_MODE = True
        return Context(config=cfg)

    def test_resized_gif_keeps_transparent_pixels(self):
        engine = Engine(self.get_context())
        engine.image = engine.create_image(
            make_palette_gif_with_transparent_background()
        )
        engine.resize(40, 25)
        result = engine.read(extension=".gif")

        output = Image.open(BytesIO(result))
        rgba = output.convert("RGBA")
        transparent = sum(1 for px in rgba.getdata() if px[3] < 128)

        assert "transparency" in output.info
        assert transparent > 0
