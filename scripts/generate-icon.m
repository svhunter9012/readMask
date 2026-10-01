#import <AppKit/AppKit.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) return 1;
        NSBitmapImageRep *bitmap = [[NSBitmapImageRep alloc]
            initWithBitmapDataPlanes:NULL pixelsWide:1024 pixelsHigh:1024
            bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO
            colorSpaceName:NSDeviceRGBColorSpace bytesPerRow:0 bitsPerPixel:0];
        NSGraphicsContext *context = [NSGraphicsContext graphicsContextWithBitmapImageRep:bitmap];
        [NSGraphicsContext saveGraphicsState];
        [NSGraphicsContext setCurrentContext:context];

        [[NSColor colorWithCalibratedRed:0.13 green:0.19 blue:0.20 alpha:1] setFill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(24, 24, 976, 976)
                xRadius:210 yRadius:210] fill];

        [[NSColor colorWithCalibratedRed:0.95 green:0.97 blue:0.91 alpha:1] setFill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(115, 445, 794, 174)
                xRadius:24 yRadius:24] fill];

        [[NSColor colorWithCalibratedRed:0.19 green:0.28 blue:0.29 alpha:1] setFill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(205, 552, 610, 17)
                xRadius:8 yRadius:8] fill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(205, 503, 505, 17)
                xRadius:8 yRadius:8] fill];

        [[NSColor colorWithCalibratedRed:0.38 green:0.76 blue:0.60 alpha:1] setFill];
        [[NSBezierPath bezierPathWithRoundedRect:NSMakeRect(554, 377, 200, 58)
                xRadius:29 yRadius:29] fill];

        [context flushGraphics];
        [NSGraphicsContext restoreGraphicsState];
        NSData *data = [bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
        return [data writeToFile:[NSString stringWithUTF8String:argv[1]] atomically:YES] ? 0 : 1;
    }
}
