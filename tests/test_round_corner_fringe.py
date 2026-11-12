# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from thumbor.ext.filters import _round_corner

WIDTH = 100
HEIGHT = 100
RADIUS = 50


def _apply_transparent_round_corner():
    # Solid white source, fully opaque, RGBA.
    source = bytearray(b"\xff\xff\xff\xff" * (WIDTH * HEIGHT))
    data = _round_corner.apply(
        1,
        "RGBA",
        RADIUS,
        RADIUS,
        255,
        0,
        0,
        WIDTH,
        HEIGHT,
        bytes(source),
        1,
    )
    return data


def test_transparent_round_corner_has_no_dark_opaque_edge_pixels():
    # Edge pixels on the arc must fade through alpha. They must not stay
    # fully opaque with their color scaled toward black.
    data = _apply_transparent_round_corner()

    dark_opaque = []
    for i in range(WIDTH * HEIGHT):
        r, g, b, a = data[i * 4 : i * 4 + 4]
        if a == 255 and min(r, g, b) < 128:
            dark_opaque.append((i % WIDTH, i // WIDTH, (r, g, b, a)))

    assert dark_opaque == [], (
        f"{len(dark_opaque)} opaque pixels are darker than the white source"
        f" along the rounded corner, e.g. {dark_opaque[:3]}"
    )
