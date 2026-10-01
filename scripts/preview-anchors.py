#!/usr/bin/env python3
"""Render both anchor controls for a quick visual check during development."""

import sys
from pathlib import Path

from AppKit import (
    NSBitmapImageFileTypePNG,
    NSBitmapImageRep,
    NSColor,
    NSDeviceRGBColorSpace,
    NSGraphicsContext,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from readmask import AnchorView, anchor_dimensions, rect


def render(kind, size, path):
    width, height = anchor_dimensions(kind, size)
    bitmap = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, int(width), int(height), 8, 4, True, False,
        NSDeviceRGBColorSpace, 0, 0,
    )
    context = NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(context)
    NSColor.clearColor().setFill()
    view = AnchorView.alloc().initWithFrame_(rect(0, 0, width, height))
    view.kind = kind
    view.drawRect_(view.bounds())
    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    data = bitmap.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
    data.writeToFile_atomically_(path, True)


if __name__ == "__main__":
    render("move", 48, sys.argv[1])
    render("resize", 48, sys.argv[2])
