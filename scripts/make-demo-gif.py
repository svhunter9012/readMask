#!/usr/bin/python3
"""Export a short, cropped GIF from a macOS screen recording.

Requires the system Python with PyObjC's AVFoundation and Quartz bridges.
"""

import argparse
from pathlib import Path

import AVFoundation
import CoreMedia
import Quartz

NSURL = AVFoundation.NSURL


def frame_at(generator, seconds):
    time = CoreMedia.CMTimeMakeWithSeconds(seconds, 600)
    image, _ = generator.copyCGImageAtTime_actualTime_error_(time, None, None)
    return image


def scaled_crop(image, crop, width):
    x, y, crop_width, crop_height = crop
    if not (0 <= x < Quartz.CGImageGetWidth(image)
            and 0 <= y < Quartz.CGImageGetHeight(image)
            and x + crop_width <= Quartz.CGImageGetWidth(image)
            and y + crop_height <= Quartz.CGImageGetHeight(image)):
        raise ValueError("crop exceeds the source video dimensions")
    cropped = Quartz.CGImageCreateWithImageInRect(
        image, Quartz.CGRectMake(x, y, crop_width, crop_height)
    )
    height = round(width * crop_height / crop_width)
    context = Quartz.CGBitmapContextCreate(
        None, width, height, 8, 0, Quartz.CGColorSpaceCreateDeviceRGB(),
        Quartz.kCGImageAlphaPremultipliedLast,
    )
    Quartz.CGContextDrawImage(
        context, Quartz.CGRectMake(0, 0, width, height), cropped
    )
    return Quartz.CGBitmapContextCreateImage(context)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--duration", type=float, default=6)
    parser.add_argument("--fps", type=float, default=6)
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--samples", action="store_true", help="write PNG samples instead of a GIF")
    args = parser.parse_args()

    asset = AVFoundation.AVURLAsset.URLAssetWithURL_options_(
        NSURL.fileURLWithPath_(str(args.video.resolve())), None
    )
    video_duration = CoreMedia.CMTimeGetSeconds(asset.duration())
    if args.start < 0 or args.duration <= 0 or args.fps <= 0 or args.width <= 0:
        parser.error("start, duration, fps and width must be valid positive values")
    if args.start + args.duration > video_duration:
        parser.error("selected clip exceeds video duration")

    generator = AVFoundation.AVAssetImageGenerator.assetImageGeneratorWithAsset_(asset)
    generator.setAppliesPreferredTrackTransform_(True)
    generator.setRequestedTimeToleranceBefore_(CoreMedia.CMTimeMake(0, 600))
    generator.setRequestedTimeToleranceAfter_(CoreMedia.CMTimeMake(0, 600))
    first = frame_at(generator, args.start)
    crop = args.crop or (0, 0, Quartz.CGImageGetWidth(first), Quartz.CGImageGetHeight(first))
    count = round(args.duration * args.fps)
    frames = (scaled_crop(frame_at(generator, args.start + index / args.fps), crop, args.width)
              for index in range(count))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.samples:
        for index, image in enumerate(frames):
            path = args.output.parent / f"{args.output.stem}-{index:02d}.png"
            destination = Quartz.CGImageDestinationCreateWithURL(
                NSURL.fileURLWithPath_(str(path.resolve())), "public.png", 1, None
            )
            Quartz.CGImageDestinationAddImage(destination, image, None)
            if not Quartz.CGImageDestinationFinalize(destination):
                raise RuntimeError(f"could not write {path}")
    else:
        destination = Quartz.CGImageDestinationCreateWithURL(
            NSURL.fileURLWithPath_(str(args.output.resolve())),
            "com.compuserve.gif", count, None,
        )
        Quartz.CGImageDestinationSetProperties(destination, {
            Quartz.kCGImagePropertyGIFDictionary: {
                Quartz.kCGImagePropertyGIFLoopCount: 0,
            },
        })
        for image in frames:
            Quartz.CGImageDestinationAddImage(destination, image, {
                Quartz.kCGImagePropertyGIFDictionary: {
                    Quartz.kCGImagePropertyGIFDelayTime: 1 / args.fps,
                },
            })
        if not Quartz.CGImageDestinationFinalize(destination):
            raise RuntimeError(f"could not write {args.output}")


if __name__ == "__main__":
    main()
