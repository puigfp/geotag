# geotag

## Use case

- you have camera that doesn't have a built-in GPS chip
- you let Google harvest your location history
- you want to add GPS EXIF metadata to the files produced by your camera

## Usage

**make a separate copy of your photos/videos before using this script**

This script is a single Python 3 file that doesn't have any Python dependencies (beside modules from the Python standard library) that you'll probably need to modify a little bit to make it fit your use case. Download [this file](./geotag/geotag.py), and run it using `python geotag.py -h`.

You'll need to download your Location History from [Google Takeout](https://takeout.google.com/settings/takeout) in JSON format.

You'll need to have [`exiftool`](https://exiftool.org/) installed on your machine an in your `PATH`. On macOS, you can install it with `brew install exiftool`. The script uses `exiftool`'s JSON API to read/write EXIF to your files.

## Warning: Timezones

Unfortunately, the EXIF metadata don't specify the timezone where the picture was taken. Therefore, this script assumes that the datetime is in the UTC timezone.

You may want to update the script to change this behavior.

## References

- [ExifTool by Phil Harvey](https://exiftool.org/)
- [Photo geotagging using your Google location history](https://chuckleplant.github.io/2018/07/23/google-photos-geotag.html)
