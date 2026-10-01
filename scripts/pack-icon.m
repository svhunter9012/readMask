#import <Foundation/Foundation.h>

static void appendUInt32(NSMutableData *data, uint32_t value) {
    uint32_t bigEndian = CFSwapInt32HostToBig(value);
    [data appendBytes:&bigEndian length:sizeof(bigEndian)];
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 3) return 2;
        NSString *directory = [NSString stringWithUTF8String:argv[1]];
        NSString *output = [NSString stringWithUTF8String:argv[2]];
        NSArray<NSArray<NSString *> *> *entries = @[
            @[@"icp4", @"icon_16x16.png"],
            @[@"icp5", @"icon_32x32.png"],
            @[@"icp6", @"icon_32x32@2x.png"],
            @[@"ic07", @"icon_128x128.png"],
            @[@"ic08", @"icon_256x256.png"],
            @[@"ic09", @"icon_512x512.png"],
            @[@"ic10", @"icon_512x512@2x.png"]
        ];

        NSMutableData *body = [NSMutableData data];
        for (NSArray<NSString *> *entry in entries) {
            NSData *png = [NSData dataWithContentsOfFile:
                [directory stringByAppendingPathComponent:entry[1]]];
            if (!png) return 1;
            [body appendData:[entry[0] dataUsingEncoding:NSASCIIStringEncoding]];
            appendUInt32(body, (uint32_t)png.length + 8);
            [body appendData:png];
        }

        NSMutableData *icon = [NSMutableData data];
        [icon appendData:[@"icns" dataUsingEncoding:NSASCIIStringEncoding]];
        appendUInt32(icon, (uint32_t)body.length + 8);
        [icon appendData:body];
        return [icon writeToFile:output atomically:YES] ? 0 : 1;
    }
}
