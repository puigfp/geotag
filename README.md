# geotag

## Use case

- your camera doesn't have a built-in GPS chip
- you let Google harvest your location history
- you want to add GPS EXIF metadata to the files produced by your camera

## Usage

**make a separate copy of your photos/videos before using this script**

This script is a single Python 3 file that doesn't have any Python dependencies (beside modules from the Python standard library) that you'll probably need to modify a little bit to make it fit your use case. Download [this file](./geotag/geotag.py), and run it using `python geotag.py -h`.

You'll need to download your Location History from [Google Takeout](https://takeout.google.com/settings/takeout) in JSON format.

You'll need to have [`exiftool`](https://exiftool.org/) installed on your machine an in your `PATH`. On macOS, you can install it with `brew install exiftool`. The script uses `exiftool`'s JSON API to read/write EXIF to your files.

## Notes

### Timezones

Unfortunately, the EXIF metadata don't specify the timezone where the picture was taken. Therefore, you must provide the `--utc-offset` flag if your camera doesn't use UTC time.

### ExifTool can already geotag pictures

Using the [`-geotag` command](https://exiftool.org/geotag.html#geotag) and a KML export of the location history, exiftool can almost do the same thing as this script. However, using a script such as this one gives me more control:

- applying some preprocessing to the location history (GPS data is noisy, and removing absurd GPS data points can make the results a lot better)
- overwriting already existing GPS data or not
- ...

## References

- [ExifTool by Phil Harvey](https://exiftool.org/)
- [Photo geotagging using your Google location history](https://chuckleplant.github.io/2018/07/23/google-photos-geotag.html)
