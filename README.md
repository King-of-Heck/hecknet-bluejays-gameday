# Bluejays Gameday

Monitors live Toronto Blue Jays games and prints lineup, home run and final-score receipts.

Watches a live game through the MLB Stats API and prints three receipts:

- **Play ball** at first pitch, with the batting lineup showing AVG and OPS,
  and both starting pitchers with ERA and FIP
- **Home run**, with exit velocity, launch angle and distance
- **Final**, with an inning-by-inning box score and R/H/E totals

FIP is not exposed by the API and is calculated locally from the standard
formula. Statcast numbers come from the Baseball Savant live gamefeed, which
is what the Savant gamefeed page itself polls; a home run receipt is held back
until those numbers land, or until `HR_STAT_TIMEOUT` elapses.

## Polling behaviour

There is no live polling before a game. The script checks the schedule, then
sleeps in hourly chunks until ten minutes before first pitch, re-checking the
schedule on each wake so postponements and start-time changes are picked up.

Doubleheaders are handled: once game one is final, game two is picked up from
the same day's schedule rather than being skipped until the next day.

## Configuration

`TEAM_ID` is 141 for Toronto. Point it at another team and the receipts follow
that team instead, though the wording is Toronto-specific in places.

## Requirements

- Windows. Printing goes through the Win32 GDI API.
- Python 3.10 or later.
- An 80mm thermal printer installed as a Windows printer. Built against an
  XP-80C at 203 DPI; other 80mm printers should work if the DPI matches.

```bash
pip install -r requirements.txt
```

Set `PRINTER_NAME` in `bluejays_gameday.py` to the printer's name as it appears in
Settings > Printers & scanners.

Receipts are rendered as images at 4x and downsampled before printing, which
is what keeps the text dark and legible on a thermal head. Courier is used
throughout; glyphs Courier lacks are composited from Segoe UI Emoji.

## Running

```bash
python bluejays_gameday.py
```

## A note on the history

Source files for 1.3 and 1.15 were not retained. The 1.15 fix (games running past midnight) is folded into the 1.7.0 commit, which is the first file that contains it.

## Versioning

Tagged releases, with the change notes in [CHANGELOG.md](CHANGELOG.md).

## Licence

MIT. See [LICENSE](LICENSE).
