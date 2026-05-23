"""
BlueJays_GameDay_1_0.py
Monitors live Toronto Blue Jays games via the MLB Stats API (GUMBO feed)
and prints thermal receipts for three events:

  1. GAME START  — "PLAY BALL!" + Blue Jays batting lineup with AVG,
                   and starting pitcher with ERA.
  2. HOME RUN    — "HOME RUN BLUE JAYS!" + player name, launch angle,
                   exit velocity, distance, current score.
  3. GAME END    — "JAYS WIN!" or "JAYS LOSE :(" depending on result.

All receipts use the standard HeckNet 💀 HeckNet 💀 header.
"""

import time
import requests
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageWin
import win32ui


PRINTER_NAME = "XP-80C"
FONT_PATH    = "cour.ttf"
FONT_BOLD    = "courbd.ttf"

FONT_SIZE       = 28           # body text point size
SKULL_FONT_SIZE = 22           # 💀 glyph point size
RENDER_SCALE    = 4

PRINTER_DPI = 203
PAPER_MM    = 80
PAPER_PX    = int(PAPER_MM / 25.4 * PRINTER_DPI)   # ≈ 638 px
MARGIN_PX   = 10
TEXT_PX     = PAPER_PX - 2 * MARGIN_PX

POLL_INTERVAL    = 15    # seconds between live-feed polls during a game
IDLE_INTERVAL    = 60    # seconds between schedule checks when no game is live
HR_STAT_TIMEOUT  = 120   # seconds to wait for Statcast hitData before printing anyway

BLUE_JAYS_TEAM_ID = 141


MLB_BASE    = "https://statsapi.mlb.com/api/v1"
MLB_BASE_11 = "https://statsapi.mlb.com/api/v1.1"
HEADERS     = {"User-Agent": "hecknet-gamday/1.0"}


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get(url: str, params: dict = None) -> dict:
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def find_todays_jays_game() -> dict | None:
    """Return the game dict for today's Blue Jays game, or None."""
    today = date.today().strftime("%Y-%m-%d")
    data  = get(f"{MLB_BASE}/schedule",
                params={"sportId": 1, "teamId": BLUE_JAYS_TEAM_ID,
                        "date": today, "hydrate": "team,linescore"})
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            return game   # first (usually only) game today
    return None


def get_live_feed(game_pk: int) -> dict:
    return get(f"{MLB_BASE_11}/game/{game_pk}/feed/live")


def get_player_stats(player_id: int, group: str, season: int) -> dict:
    """Fetch season stats for a player. group: 'hitting' or 'pitching'."""
    data = get(f"{MLB_BASE}/people/{player_id}",
               params={"hydrate": f"stats(group={group},type=season,season={season})"})
    people = data.get("people", [])
    if not people:
        return {}
    for stat_block in people[0].get("stats", []):
        if stat_block.get("group", {}).get("displayName", "").lower() == group:
            splits = stat_block.get("splits", [])
            if splits:
                return splits[0].get("stat", {})
    return {}


def load_font(bold=False, size=None):
    size = size or FONT_SIZE
    path = FONT_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size * RENDER_SCALE)
    except OSError:
        return ImageFont.load_default()


_SKULL_FONT_CANDIDATES = [
    "seguiemj.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
    "seguisym.ttf",
]


def load_skull_font(size=None):
    size = size or SKULL_FONT_SIZE
    for path in _SKULL_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size * RENDER_SCALE)
        except OSError:
            continue
    return load_font(bold=True, size=size)


SKULL_Y_OFFSET = 36


def draw_skull_header(draw, text: str, font_text, font_skull, paper_w: int, y: int):
    """Render  💀  <text>  💀  centred on the line."""
    SKULL   = "\U0001F480"
    gap     = int(font_text.size * 0.4)
    skull_w = int(font_skull.getlength(SKULL))
    text_w  = int(font_text.getlength(text))
    total_w = skull_w + gap + text_w + gap + skull_w
    x = (paper_w - total_w) // 2
    draw.text((x, y + SKULL_Y_OFFSET), SKULL, font=font_skull, fill="black")
    x += skull_w + gap
    draw.text((x, y), text, font=font_text, fill="black")
    x += text_w + gap
    draw.text((x, y + SKULL_Y_OFFSET), SKULL, font=font_skull, fill="black")


def word_wrap(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if font.getlength(candidate) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def _render(ops: list, top_pad: int = 0) -> Image.Image:
    """
    ops: list of (text, font, align)  where align is 'left' | 'center'
    Returns a cropped, downsampled RGB image ready to print.
    """
    S       = RENDER_SCALE
    paper_w = PAPER_PX * S
    margin  = MARGIN_PX * S
    line_h  = (FONT_SIZE + 5) * S

    total_h = len(ops) * line_h + line_h * 2 + top_pad
    hi_res  = Image.new("RGB", (paper_w, total_h), "white")
    draw    = ImageDraw.Draw(hi_res)
    y       = margin // 2 + top_pad

    for text, font, align in ops:
        if align == "center":
            bbox = font.getbbox(text)
            tw   = bbox[2] - bbox[0]
            x    = (paper_w - tw) / 2 - bbox[0]
        else:
            x = margin
        draw.text((x, y), text, font=font, fill="black")
        y += line_h

    out_w  = PAPER_PX
    out_h  = int(total_h / S)
    output = hi_res.resize((out_w, out_h), Image.LANCZOS)
    output = ImageEnhance.Contrast(output).enhance(2.5).convert("L").convert("RGB")
    return output.crop((0, 0, out_w, int(y / S) + 4))


def _base_ops(font_n, font_b, font_sm):
    """Return (ops list, div lambda, add lambda) wired to the font set."""
    ops    = []
    text_w = TEXT_PX * RENDER_SCALE
    DIVIDER = "─" * int(text_w / (FONT_SIZE * RENDER_SCALE * 0.62))

    def add(text, bold=False, align="left", small=False):
        ops.append((text, font_sm if small else (font_b if bold else font_n), align))

    def div():
        add(DIVIDER)

    return ops, add, div, DIVIDER


def build_hecknet_header(ops, add, div, font_b, font_skull, hi_res_ref: list):
    """
    Add a blank placeholder line for the skull header into ops.
    After _render() is called, the caller must composite the skull header
    onto the returned image — but since we rebuilt the rendering inline,
    we do it differently: we return all data and let the build functions
    draw directly.
    """
    pass


def _render_with_skull_header(ops: list, header_line_idx: int) -> Image.Image:
    """
    Like _render(), but composites 💀 HeckNet 💀 over the line at header_line_idx.
    """
    S       = RENDER_SCALE
    paper_w = PAPER_PX * S
    margin  = MARGIN_PX * S
    line_h  = (FONT_SIZE + 5) * S
    top_pad = SKULL_Y_OFFSET

    font_b     = load_font(bold=True)
    font_skull = load_skull_font()

    total_h = len(ops) * line_h + line_h * 2 + top_pad
    hi_res  = Image.new("RGB", (paper_w, total_h), "white")
    draw    = ImageDraw.Draw(hi_res)
    y       = margin // 2 + top_pad

    for i, (text, font, align) in enumerate(ops):
        if i == header_line_idx:
            draw_skull_header(draw, "HeckNet", font_b, font_skull, paper_w,
                              margin // 2 + top_pad)
            y += line_h
            continue
        if align == "center":
            bbox = font.getbbox(text)
            tw   = bbox[2] - bbox[0]
            x    = (paper_w - tw) / 2 - bbox[0]
        else:
            x = margin
        draw.text((x, y), text, font=font, fill="black")
        y += line_h

    out_w  = PAPER_PX
    out_h  = int(total_h / S)
    output = hi_res.resize((out_w, out_h), Image.LANCZOS)
    output = ImageEnhance.Contrast(output).enhance(2.5).convert("L").convert("RGB")
    return output.crop((0, 0, out_w, int(y / S) + 4))


def build_play_ball(lineup: list[dict], pitcher: dict,
                    opponent: str, game_time: str) -> Image.Image:
    """
    lineup: [{"name": str, "avg": str, "position": str}, ...]  (batting order)
    pitcher: {"name": str, "era": str}
    """
    font_n  = load_font(bold=False)
    font_b  = load_font(bold=True)
    font_sm = load_font(bold=False, size=FONT_SIZE - 6)
    text_w  = TEXT_PX * RENDER_SCALE
    DIVIDER = "─" * int(text_w / (FONT_SIZE * RENDER_SCALE * 0.62))

    ops = []
    skull_idx = 0   # first line is the skull placeholder

    def add(text, bold=False, align="left", small=False):
        ops.append((text, font_sm if small else (font_b if bold else font_n), align))

    def div():
        add(DIVIDER)

    add("", align="center")
    div()
    add("PLAY BALL!", bold=True, align="center")
    add(f"TOR vs {opponent}", align="center", small=True)
    add(game_time, align="center", small=True)
    div()

    add("BATTING ORDER", bold=True)
    for i, batter in enumerate(lineup, 1):
        pos  = batter.get("position", "  ")[:2].upper()
        name = batter["name"]
        avg  = batter.get("avg", ".---")
        line = f"{i}. {pos} {name}"
        for wl in word_wrap(line, font_n, text_w):
            add(wl)
        add(f"   AVG: {avg}", small=True)

    div()

    add("STARTING PITCHER", bold=True)
    add(pitcher["name"])
    add(f"ERA: {pitcher.get('era', '-.--')}", small=True)
    div()

    return _render_with_skull_header(ops, skull_idx)


def build_home_run(player_name: str, launch_angle, exit_velo, distance,
                   jays_score: int, opp_score: int, opp_name: str,
                   inning: int, inning_half: str) -> Image.Image:
    font_n  = load_font(bold=False)
    font_b  = load_font(bold=True)
    font_sm = load_font(bold=False, size=FONT_SIZE - 6)
    text_w  = TEXT_PX * RENDER_SCALE
    DIVIDER = "─" * int(text_w / (FONT_SIZE * RENDER_SCALE * 0.62))

    ops = []

    def add(text, bold=False, align="left", small=False):
        ops.append((text, font_sm if small else (font_b if bold else font_n), align))

    def div():
        add(DIVIDER)

    add("", align="center")   # skull placeholder at index 0
    div()
    add("HOME RUN", bold=True, align="center")
    add("BLUE JAYS!!", bold=True, align="center")
    div()

    add(player_name, bold=True, align="center")
    add("")

    if exit_velo is not None:
        add(f"Exit Velo : {exit_velo:.1f} mph")
    if launch_angle is not None:
        add(f"Launch Ang: {launch_angle:.1f}\u00b0")
    if distance is not None:
        add(f"Distance  : {distance:.0f} ft")

    div()

    inn_str = f"{'Top' if inning_half == 'top' else 'Bot'} {inning}"
    add(f"{inn_str}", small=True, align="center")
    add(f"TOR {jays_score}  –  {opp_score} {opp_name[:3].upper()}",
        bold=True, align="center")
    div()

    return _render_with_skull_header(ops, 0)


def build_game_end(jays_win: bool, jays_score: int, opp_score: int,
                   opp_name: str) -> Image.Image:
    font_n  = load_font(bold=False)
    font_b  = load_font(bold=True)
    font_sm = load_font(bold=False, size=FONT_SIZE - 6)
    text_w  = TEXT_PX * RENDER_SCALE
    DIVIDER = "─" * int(text_w / (FONT_SIZE * RENDER_SCALE * 0.62))

    ops = []

    def add(text, bold=False, align="left", small=False):
        ops.append((text, font_sm if small else (font_b if bold else font_n), align))

    def div():
        add(DIVIDER)

    add("", align="center")   # skull placeholder at index 0
    div()

    if jays_win:
        add("JAYS WIN!", bold=True, align="center")
    else:
        add("JAYS LOSE :(", bold=True, align="center")

    div()
    add(f"TOR {jays_score}  –  {opp_score} {opp_name[:3].upper()}",
        align="center")
    div()

    return _render_with_skull_header(ops, 0)


def send_to_printer(img: Image.Image):
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(PRINTER_NAME)
    pw = hdc.GetDeviceCaps(110)
    if img.width != pw:
        img = img.resize((pw, int(img.height * pw / img.width)), Image.LANCZOS)
    hdc.StartDoc("HeckNet GameDay")
    hdc.StartPage()
    ImageWin.Dib(img).draw(hdc.GetHandleOutput(), (0, 0, img.width, img.height))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


def build_lineup_data(live: dict) -> tuple[list[dict], dict]:
    """
    Returns (batting_lineup, starting_pitcher) parsed from the GUMBO feed.
    batting_lineup: list of {name, position, avg}
    starting_pitcher: {name, era}
    """
    season    = date.today().year
    game_data = live.get("gameData", {})
    players   = game_data.get("players", {})
    box       = live.get("liveData", {}).get("boxscore", {})
    jays_side = _jays_side(live)
    team_box  = box.get("teams", {}).get(jays_side, {})

    batting_order  = team_box.get("battingOrder", [])
    pitchers_list  = team_box.get("pitchers", [])

    def player_info(pid: int) -> dict:
        return players.get(f"ID{pid}", {})

    lineup = []
    for pid in batting_order:
        info     = player_info(pid)
        name     = info.get("boxscoreName") or info.get("fullName", f"#{pid}")
        pos_code = info.get("primaryPosition", {}).get("abbreviation", "")
        try:
            stats = get_player_stats(pid, "hitting", season)
            avg   = stats.get("avg", ".---")
        except Exception:
            avg = ".---"
        lineup.append({"name": name, "position": pos_code, "avg": avg})
        time.sleep(0.1)   # gentle on the API

    pitcher_data = {"name": "Unknown", "era": "-.--"}
    if pitchers_list:
        sp_id = pitchers_list[0]
        info  = player_info(sp_id)
        name  = info.get("boxscoreName") or info.get("fullName", f"#{sp_id}")
        try:
            stats = get_player_stats(sp_id, "pitching", season)
            era   = stats.get("era", "-.--")
        except Exception:
            era = "-.--"
        pitcher_data = {"name": name, "era": era}

    return lineup, pitcher_data


def _jays_side(live: dict) -> str:
    """Returns 'home' or 'away' for the Blue Jays in this game."""
    teams = live.get("gameData", {}).get("teams", {})
    if teams.get("home", {}).get("id") == BLUE_JAYS_TEAM_ID:
        return "home"
    return "away"


def _opp_name(live: dict) -> str:
    teams    = live.get("gameData", {}).get("teams", {})
    jays_sid = _jays_side(live)
    opp_sid  = "away" if jays_sid == "home" else "home"
    return teams.get(opp_sid, {}).get("teamName", "OPP")


def _score(live: dict) -> tuple[int, int]:
    """Returns (jays_score, opp_score)."""
    linescore = live.get("liveData", {}).get("linescore", {})
    teams     = linescore.get("teams", {})
    jays_sid  = _jays_side(live)
    opp_sid   = "away" if jays_sid == "home" else "home"
    jays_r    = teams.get(jays_sid, {}).get("runs", 0) or 0
    opp_r     = teams.get(opp_sid,  {}).get("runs", 0) or 0
    return jays_r, opp_r


def _abstract_state(live: dict) -> str:
    return (live.get("gameData", {})
                .get("status", {})
                .get("abstractGameState", ""))


def _coded_state(live: dict) -> str:
    return (live.get("gameData", {})
                .get("status", {})
                .get("codedGameState", ""))


def _current_inning(live: dict) -> tuple[int, str]:
    ls = live.get("liveData", {}).get("linescore", {})
    return ls.get("currentInning", 0), ls.get("inningHalf", "top").lower()


def monitor():
    print(f"[{ts()}] HeckNet GameDay starting — monitoring Blue Jays (team {BLUE_JAYS_TEAM_ID})")

    while True:
        game = None
        try:
            game = find_todays_jays_game()
        except Exception as e:
            print(f"[{ts()}] Schedule fetch error: {e}")

        if not game:
            print(f"[{ts()}] No Blue Jays game today. Checking again in {IDLE_INTERVAL}s…")
            time.sleep(IDLE_INTERVAL)
            continue

        game_pk   = game["gamePk"]
        state     = game.get("status", {}).get("abstractGameState", "")
        print(f"[{ts()}] Game found: pk={game_pk}, state={state}")

        if state == "Final":
            print(f"[{ts()}] Game already final. Nothing to monitor today.")
            time.sleep(IDLE_INTERVAL * 10)
            continue

        printed_start = False
        printed_end   = False
        done_play_ids: set[str] = set()
        # Plays detected as Jays HRs but waiting for Statcast data.
        # key: play_id    value: dict with snapshot data + first_seen timestamp
        pending_hrs: dict[str, dict] = {}

        print(f"[{ts()}] Entering game monitor loop for game {game_pk}…")

        while True:
            try:
                live = get_live_feed(game_pk)
            except Exception as e:
                print(f"[{ts()}] Live feed error: {e}")
                time.sleep(POLL_INTERVAL)
                continue

            abstract = _abstract_state(live)
            coded    = _coded_state(live)
            print(f"[{ts()}] State={abstract}/{coded}", end="")

            jays_score, opp_score = _score(live)
            opp = _opp_name(live)
            inning, half = _current_inning(live)
            print(f"Score TOR {jays_score}–{opp_score} {opp}  Inn={half} {inning}")

            if not printed_start and abstract == "Live":
                print(f"[{ts()}] Game started — building lineup receipt…")
                try:
                    lineup, pitcher = build_lineup_data(live)
                    g_time = (live.get("gameData", {})
                                  .get("datetime", {})
                                  .get("time", ""))
                    ampm   = (live.get("gameData", {})
                                  .get("datetime", {})
                                  .get("ampm", ""))
                    game_time_str = f"{g_time} {ampm} ET" if g_time else ""
                    img = build_play_ball(lineup, pitcher, opp, game_time_str)
                    send_to_printer(img)
                    printed_start = True
                    print(f"[{ts()}]  Play Ball receipt printed.")
                except Exception as e:
                    print(f"[{ts()}]  Play Ball print error: {e}")
                    printed_start = True   # don't retry endlessly

            if abstract == "Live":
                all_plays = (live.get("liveData", {})
                                 .get("plays", {})
                                 .get("allPlays", []))
                jays_side = _jays_side(live)

                play_by_id: dict[str, dict] = {}
                for play in all_plays:
                    about   = play.get("about", {})
                    result  = play.get("result", {})
                    play_id = str(about.get("atBatIndex", "")
                                  or result.get("description", "")[:40])
                    play_by_id[play_id] = play

                for play_id, play in play_by_id.items():
                    if play_id in done_play_ids or play_id in pending_hrs:
                        continue

                    result      = play.get("result", {})
                    about       = play.get("about", {})
                    event_type  = result.get("eventType", "")
                    if event_type != "home_run":
                        continue

                    half_inning    = about.get("halfInning", "")
                    batter_is_jays = (
                        (jays_side == "away" and half_inning == "top") or
                        (jays_side == "home" and half_inning == "bottom")
                    )
                    if not batter_is_jays:
                        done_play_ids.add(play_id)
                        continue

                    matchup     = play.get("matchup", {})
                    batter_name = matchup.get("batter", {}).get("fullName", "Unknown")
                    hr_inning   = about.get("inning", inning)
                    hr_half     = half_inning or half
                    hr_jays     = result.get("homeScore") if jays_side == "home" else result.get("awayScore")
                    hr_opp      = result.get("awayScore") if jays_side == "home" else result.get("homeScore")
                    if hr_jays is None:
                        hr_jays = jays_score
                    if hr_opp is None:
                        hr_opp = opp_score

                    pending_hrs[play_id] = {
                        "batter_name": batter_name,
                        "hr_inning":   hr_inning,
                        "hr_half":     hr_half,
                        "hr_jays":     hr_jays,
                        "hr_opp":      hr_opp,
                        "opp":         opp,
                        "first_seen":  time.monotonic(),
                    }
                    print(f"[{ts()}]  HR detected — {batter_name} (waiting for Statcast…)")

                for play_id in list(pending_hrs.keys()):
                    info = pending_hrs[play_id]

                    play      = play_by_id.get(play_id, {})
                    hit_data  = play.get("hitData", {})
                    exit_velo = hit_data.get("launchSpeed")
                    launch_ang = hit_data.get("launchAngle")
                    distance  = hit_data.get("totalDistance")

                    all_present = (exit_velo is not None
                                   and launch_ang is not None
                                   and distance is not None)
                    timed_out   = (time.monotonic() - info["first_seen"]
                                   >= HR_STAT_TIMEOUT)

                    if not all_present and not timed_out:
                        print(f"[{ts()}]   ⏳ Still waiting for Statcast on {info['batter_name']}…")
                        continue

                    done_play_ids.add(play_id)
                    del pending_hrs[play_id]

                    if timed_out and not all_present:
                        print(f"[{ts()}]     Statcast timeout for {info['batter_name']} — printing without metrics.")

                    print(f"[{ts()}]   Printing HR receipt — {info['batter_name']} "
                          f"EV={exit_velo}  LA={launch_ang}  Dist={distance}")
                    try:
                        img = build_home_run(
                            info["batter_name"], launch_ang, exit_velo, distance,
                            info["hr_jays"], info["hr_opp"], info["opp"],
                            info["hr_inning"], info["hr_half"],
                        )
                        send_to_printer(img)
                        print(f"[{ts()}]  Home Run receipt printed.")
                    except Exception as e:
                        print(f"[{ts()}]  Home Run print error: {e}")

            if not printed_end and abstract == "Final":
                print(f"[{ts()}] Game over — printing result receipt…")
                try:
                    jays_win = jays_score > opp_score
                    img = build_game_end(jays_win, jays_score, opp_score, opp)
                    send_to_printer(img)
                    printed_end = True
                    print(f"[{ts()}]  Game End receipt printed.")
                except Exception as e:
                    print(f"[{ts()}]  Game End print error: {e}")
                    printed_end = True

                print(f"[{ts()}] Game complete. Resuming idle watch.")
                break   # exit inner loop; outer loop will find no game / sleep

            if abstract == "Preview":
                print(f"[{ts()}] Game not yet started. Checking in {IDLE_INTERVAL}s…")
                time.sleep(IDLE_INTERVAL)
            else:
                time.sleep(POLL_INTERVAL)

        time.sleep(IDLE_INTERVAL * 5)


if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Stopped.")
