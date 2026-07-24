# Changelog

Version numbers were reassigned for release (the old scheme bumped the
minor version for bugfixes); the original number is in parentheses. The
notes below are from each script's own version history.

Source files for 1.3 and 1.15 were not retained. The 1.15 fix (games running past midnight) is folded into the 1.7.0 commit, which is the first file that contains it.

## 1.7.0  (originally 1.16)

Added doubleheader support. find_todays_jays_game() (singular, first game only)
replaced with find_todays_jays_games() (returns all of today's games, sorted by
game number). The outer loop now tracks a handled_pks set of game PKs that have
been fully monitored (game ended, or found already Final) and always picks the
next unhandled game from today's schedule — so game 2 of a doubleheader is picked
up automatically once game 1 finishes, instead of being skipped until the next
day. handled_pks resets when the calendar date rolls over.

## 1.6.3  (originally 1.14)

Fixed UnicodeEncodeError when piped through HeckNet Manager (Windows cp1252 can't
encode emoji). Added sys.stdout.reconfigure(UTF-8) and -u unbuffered flag support
so poll output streams in real time.

## 1.6.2  (originally 1.13)

Fixed crash on Play Ball receipt: local variable 'ops' (the OPS batting stat) was
shadowing the 'ops' render-operations list inside build_play_ball, causing 'str
has no attribute append'. Renamed to batter_ops.

## 1.6.1  (originally 1.12)

Removed diagnostic key-dump logging from get_player_stats now that field names are
confirmed.

## 1.6.0  (originally 1.11)

Confirmed via debug keys that wOBA and FIP are not in the MLB Stats API. Switched
batters to AVG + OPS (both directly available). FIP is now calculated from
available pitching stats using the standard formula ((13*HR + 3*(BB+HBP) - 2*K) /
IP) + 3.15. Removed seasonAdvanced hitting fetch (it has no stats we need); kept
it for pitching.

## 1.5.1  (originally 1.10)

Fixed blank stats: the combined double-hydrate string broke the API response
entirely (including AVG). get_player_stats now makes two sequential calls (season
then seasonAdvanced) and merges them. Added key-dump diagnostic logging on first
batter and pitchers.

## 1.5.0  (originally 1.9)

Lineup card now shows wOBA alongside AVG for each batter. Pitching matchup section
shows both starters (TOR and opponent) with ERA and FIP for each. Game-end receipt
now includes a full inning-by-inning box score printed vertically (INN/TOR/OPP
columns) with R/H/E totals.

## 1.4.2  (originally 1.8.1)

Removed the now-redundant function-local timezone imports.

## 1.4.1  (originally 1.8)

Fixed missing timedelta/timezone imports (were local-only; moved to module-level
from datetime import).

## 1.4.0  (originally 1.7)

Eliminated pre-game polling. The script checks the schedule once, reads the
scheduled start time, then sleeps in 1-hour chunks until T-10 minutes before first
pitch. Each hourly wakeup re-checks the schedule so postponements, cancellations,
and start-time changes are caught within an hour regardless of how long the script
has been running. Zero live-feed API calls during the wait.

## 1.3.1  (originally 1.6)

Fixed wrong JSON structure assumption for /gf endpoint. v1.5 looked for HR entries
under fictional team_home/team_away keys with an "events" field; the actual
structure has a top-level "exit_velocity" array containing every batted ball with
a "result" field — HRs are "result == Home Run". Diagnostic logging now also
reports total batted-ball count, so we can tell whether the endpoint is reaching
us with data at all.

## 1.3.0  (originally 1.5)

Replaced statcast_search/csv Savant endpoint with the live gamefeed endpoint
(baseballsavant.mlb.com/gf?game_pk=...). The CSV search is a batch index updated
post-game; /gf is what the Savant Gamefeed page itself polls in real-time. Field
mapping: hit_speed→launch_speed, hit_angle→launch_angle,
hit_distance→hit_distance_sc.

## 1.2.1  (originally 1.4)

Fixed scoping bug where the pending-HR flush loop ran outside the `if
pending_hrs:` block, causing savant_by_pid to be undefined or stale on the poll
when the HR is first queued. The flush loop is now correctly inside the block.
Added per-row Savant diagnostic logging (pid, name, EV, LA, Dist) so metric
availability is visible in the console on every retry.

## 1.2.0  (originally 1.2)

Switched Statcast metric source from the GUMBO hitData block (which populates with
an unreliable delay) to the Baseball Savant CSV search endpoint
(/statcast_search/csv?game_pk=…&events=home_run), the same feed powering the
Savant gamefeed. Pending HRs are now matched to Savant rows by batter MLBAM
player_id; the GUMBO feed is still used for all other game-state detection.

## 1.1.0  (originally 1.1)

Home run receipts now wait for Statcast data before printing. HR plays are held in
a pending dict on first detection; each poll re-checks hitData until launchSpeed,
launchAngle, and totalDistance are all present (or HR_STAT_TIMEOUT seconds
elapse), then prints.

## 1.0.0  (originally 1.0)

Initial release. Polls MLB Stats API every 15 seconds for today's Blue Jays game.
Detects game start, home runs (Blue Jays only), and game end. Fetches season
batting AVG for each lineup batter and ERA for starting pitcher from the statsapi
hydrated player stats endpoint. Renders receipts using the same 4× supersampling
pipeline as the rest of the HeckNet ecosystem (Courier, Segoe UI Emoji skulls).

