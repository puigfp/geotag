# geotag

## Use case

- your camera doesn't have a built-in GPS chip
- you let Google harvest your location history
- you want to add GPS EXIF metadata to the files produced by your camera

## Usage

**make a backup of your photos/videos before using this code**

Before running the code:

- You need to download your Location History from [Google Takeout](https://takeout.google.com/settings/takeout) in JSON format.

- You need to have [`exiftool`](https://exiftool.org/) installed on your machine an in your `PATH` (the script uses `exiftool`'s JSON API to read/write EXIF to your files).

  On macOS, you can install it with `brew install exiftool`.

You'll probably need to update the code to get it to do exactly what you want, a way of doing that is:

- Install [poetry](https://python-poetry.org/).
- Clone this repository.
- Run `poetry install`, which creates a separate python environment and installs this project's dependencies inside it.
- Run `poetry shell`, which activates this python environment in you current shell.
- Running `geotag -h` should now work.
- You can modify the code, and your modified version of the code will be run when you run the `geotag` command

## Notes

### Timezones

Unfortunately, the EXIF standard only recently added a way to store the timezone in which a picture was taken (`OffsetTimeOriginal` field, EXIF Standard 2.31, July 2016). As a result, most cameras don't populate the field, which isn't ideal, considering we need to convert the `DateTimeOriginal` string to a UTC timestamp to find the closest location of the history.

If your camera doesn't populate the field, you should provide the `--utc-offset-default` flag (format: `±HH:MM`), and its value should be equal to the the offset of your camera's time with UTC time.

Once the script has added GPS metadata to the pictures, it can use that GPS location to figure out the timezone in which each picture was taken, and update the `DateTimeOriginal` and `OffsetTimeOriginal` fields with more meaningful values.  
For instance, my camera doesn't populate the timezone field, and I have configured it so that it uses UTC time. If a photo was taken in the UTC-4 timezone at 11PM, my camera saved the date as `2020.05.05 03:00AM UTC`, and the script will update that value to `2020.05.04 11:00PM UTC-4`. This allows me to make my photo management software show meaningful dates/times without having to think about updating my camera's clock when switching timezones or when DST starts.

### ExifTool can already geotag pictures

Using the [`-geotag` command](https://exiftool.org/geotag.html#geotag) and a KML export of the location history, exiftool can almost do the same thing as this script. However, using a script such as this one gives me more control:

- applying some preprocessing to the location history (GPS data is noisy, and removing absurd GPS data points can make the results a lot better)
- overwriting already existing GPS data or not, using any condition
- ...

## References

- [ExifTool by Phil Harvey](https://exiftool.org/)
- [Photo geotagging using your Google location history](https://chuckleplant.github.io/2018/07/23/google-photos-geotag.html)
