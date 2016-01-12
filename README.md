# Ticketizer

Train ticket auto-buyer for 12306.cn. Has primitive support for path-finding,
cost/time optimization, and auto-buying (assuming you have access to a captcha
solver service).

## Notice

This project is *abandoned*. Maybe the code still works, maybe it doesn't
(chances are, it doesn't). Feel free to fork the project and modify it to
your heart's content.

## License

All code is licensed under [GPLv3](http://www.gnu.org/licenses/gpl-3.0.txt).

## Disclaimer
The author of this program is in no way affiliated with 12306,
and will not be held accountable for any damage caused by using
this program. (In 21st century English: If you get banned for
using this, sucks for you.)

## Usage
`python -m ui.cli.main [--auto] [--config <path>] [--verbosity <flags>]`

### Arguments

#### `--auto`

Turns on auto-fill mode. This means that configuration values
will be used by default whenever possible, so that you will
not have to manually enter in the information.

#### `--config <path>`

Specifies the configuration script path.
Example usage: `--config "path/to/config/myconfigfile.py"`

#### `--verbosity <flags>`

Specifies the logging verbosity. The format is as follows:

- enable all logging: `all`
- disable all logging: `none`
- selectively enable logging: `[d][n][w][e]`
  - d: Debug
  - n: Network
  - w: Warning
  - e: Error