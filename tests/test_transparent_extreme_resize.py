# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

import shutil
import tempfile
from io import BytesIO
from os.path import join

from PIL import Image
from tornado.testing import gen_test

from tests.base import TestCase as ThumborBaseTestCase
from tests.handlers.test_base_handler import BaseImagingTestCase
from thumbor.config import Config
from thumbor.context import Context, ServerParameters
from thumbor.importer import Importer

BARS = [
    (255, 0, 0),
    (255, 165, 0),
    (255, 255, 0),
    (0, 128, 0),
    (0, 0, 255),
    (75, 0, 130),
    (238, 130, 238),
    (255, 255, 255),
]


def make_transparent_rainbow_png():
    # 16x16 RGBA PNG: vertical rainbow bars in the middle rows,
    # fully transparent everywhere else
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for x in range(16):
        color = BARS[x * len(BARS) // 16]
        for y in range(4, 12):
            img.putpixel((x, y), color + (255,))
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def make_wide_rainbow_png():
    # 940x2 RGBA PNG: vertical rainbow bars on both rows, same colours
    img = Image.new("RGBA", (940, 2), (0, 0, 0, 0))
    for x in range(940):
        color = BARS[x * len(BARS) // 940]
        for y in range(2):
            img.putpixel((x, y), color + (255,))
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


class TransparentExtremeResizeTestCase(BaseImagingTestCase):
    def setUp(self):
        # Write the source images before the app is built. The app is
        # built inside the parent setUp, so the loader must point at the
        # temp directory by then. BaseImagingTestCase.setUp is skipped on
        # purpose: it would point the loader at the fixtures folder.
        self.root_path = tempfile.mkdtemp()
        self.loader_path = self.root_path
        self.base_uri = "/image"
        with open(join(self.root_path, "rainbow.png"), "wb") as image_file:
            image_file.write(make_transparent_rainbow_png())
        with open(join(self.root_path, "940x2.png"), "wb") as image_file:
            image_file.write(make_wide_rainbow_png())
        ThumborBaseTestCase.setUp(self)

    def tearDown(self):
        shutil.rmtree(self.root_path)
        ThumborBaseTestCase.tearDown(self)

    def get_context(self):
        cfg = Config(SECURITY_KEY="ACME-SEC")
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = self.loader_path
        cfg.STORAGE = "thumbor.storages.file_storage"
        cfg.FILE_STORAGE_ROOT_PATH = self.root_path
        cfg.QUALITY = "keep"

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(
            8889, "localhost", "thumbor.conf", None, "info", None
        )
        server.security_key = "ACME-SEC"
        return Context(server, cfg, importer)

    @gen_test
    async def test_transparent_png_resized_to_extreme_aspect_ratio_keeps_pixels(
        self,
    ):
        response = await self.async_fetch("/unsafe/800x20/rainbow.png")
        assert response.code == 200
        img = Image.open(BytesIO(response.body)).convert("RGBA")

        assert img.size == (800, 20)
        # The source bars are opaque, so the resized strip must contain
        # opaque pixels. The bug returns a strip where every pixel is
        # fully transparent (alpha 0).
        assert img.getchannel("A").getextrema()[1] > 0

    @gen_test
    async def test_fit_in_1x1_returns_visible_image(self):
        response = await self.async_fetch("/unsafe/fit-in/1x1/940x2.png")
        assert response.code == 200
        img = Image.open(BytesIO(response.body)).convert("RGBA")

        assert img.size == (1, 1)
        # The source bars are opaque, so the 1x1 result must not be
        # fully transparent. The bug returns a 500 error page instead.
        assert img.getchannel("A").getextrema()[1] > 0

    @gen_test
    async def test_fit_in_width_only_returns_visible_image(self):
        response = await self.async_fetch("/unsafe/fit-in/100x0/940x2.png")
        assert response.code == 200
        img = Image.open(BytesIO(response.body)).convert("RGBA")

        assert img.size == (100, 1)
        # The source bars are opaque, so the 100x1 result must not be
        # fully transparent. The bug returns a 500 error page instead.
        assert img.getchannel("A").getextrema()[1] > 0
