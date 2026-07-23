# TODO

Snapshot written 2026-07-14, right before freezing this state for an extended
test run on the target hardware (Raspberry Pi Zero 2 WH). Captures the
findings from a functional diff against upstream `helgeerbe/picframe` (fetched
the same day) plus one bug found during that review.

## Critical bug: `controller.py` is missing MQTT-facing wrapper methods

**Update 2026-07-14: `brightness` fixed** (needed for the time-of-day dimming
feature below), see "Time-of-Day Brightness Dimming" in `DEVELOPMENT.md`. The
other ~14 wrappers listed below are still missing.

While cutting the video-restart logic out of `controller.py`, roughly 15
property/method wrappers that `interface_mqtt.py` calls directly were dropped
instead of being kept. The spot is marked by a stale comment:
`# ... (most property setters remain the same, just removing video specific logic)`.

Missing wrappers: `shuffle`, `fade_time`, `time_delay`,
`matting_images`, `location_filter`, `tags_filter`, `subdirectory`,
`date_from`, `date_to`, `display_is_on`, `clock_is_on`, `text_is_on()`,
`set_show_text()`, `get_directory_list()`, `get_number_of_files()`,
`purge_files()`. (`brightness` was fixed 2026-07-14, see above.)

`Model` and `ViewerDisplay` still implement all of the underlying
functionality (`fade_time`/`time_delay`/`subdirectory`/`shuffle`/
`location_filter`/`tags_filter`/`set_where_clause`/`purge_files`/
`get_directory_list` in `model.py`; `get_brightness`/`set_brightness`/
`matting_images`/`display_is_on`/`clock_is_on`/`text_is_on`/`set_show_text`/
`reset_name_tm` in `viewer_display.py`) — only the thin `Controller` wrapper
is gone.

**Impact:** any MQTT/Home Assistant command touching shuffle, date filters,
subdirectory navigation, matting, location/tags filter, text toggle,
clock/display on-off, or purge-files will raise `AttributeError` and likely
take down the MQTT handler thread. (`brightness` no longer affected, see update above.)

**Fix:** port the missing wrapper methods back from `upstream-main`'s
`controller.py` (upstream still has them, just structured differently around
its own in-process video playback). No architecture change required, should
be a mechanical port.

## Functional differences vs. upstream (`helgeerbe/picframe`, main branch, checked 2026-07-14)

Note: commit-history-based comparison (`git log`, merge-base) is unreliable
between this fork and upstream — the fork's entire history was rewritten via
`git filter-repo` on 2026-07-11 for a privacy/credential cleanup, which
changed essentially every commit hash back to the project root (filter-repo
strips commit signatures and reconstructs every commit). The comparison below
is based on a content diff of the current trees, not commit ancestry.

### Upstream has, this fork doesn't

- **In-process video playback (no restart hack).** Upstream replaced the
  "play video -> exit code 10 -> watcher.sh restarts -> resume via bookmark"
  approach with a VLC-backed subprocess (`video_player.py`, IPC over
  stdin/stdout) plus `video_streamer.py`'s `VideoStreamer` (play/pause/stop/
  kill, state listener) and `VideoFrameExtractor` (grabs first/last frame for
  a smooth cross-fade into/out of video). `viewer_display.py` exposes
  `is_video_playing()`/`pause_video()`/`stop_video()` directly, and
  `controller.py`'s `next()`/`back()`/`delete()`/`paused` all check
  `is_video_playing()` and stop the video in place instead of restarting the
  process. This is a full solution to the exact problem `CLAUDE.md` describes
  as "tried repeatedly and abandoned" here — worth a serious look, but
  adopting it means retiring `exit_code=10`/`watcher.sh`/
  `shown_albums.log`-bookmark video-restart mechanism.
- **Nominatim (geo lookup) compliance fix.** `geo_reverse.py` gained a
  required `User-Agent` header and a 2s minimum-interval rate limiter per OSM
  Nominatim's usage policy, and raised the request timeout from 3s to 30s.
  This fork has neither — real risk of an IP ban from Nominatim if
  `load_geoloc` is used.
- **get_image_meta.py refactor.** Upstream split EXIF/IPTC/XMP parsing into
  private helpers (`__do_exif_tags`, `__do_xmp_keywords`, `__find_xmp_key`,
  etc.) and added a `has_exif()` check. This fork kept the older flat
  structure, plus a fork-only `get_video_info` function upstream doesn't
  have.
- **Text positioning rework.** `text_wdt_offset_pct` was replaced by
  pixel-based, portrait-pair-aware `text_x_margin`/`text_y_margin`. This fork
  still uses the old percentage-based margin.
- **`display_power: 3` + multi-HDMI support.** New display-power option reads
  `/sys/class/drm/card{N}-{HDMI}/status`, plus a `display_hdmi` config key to
  pick which HDMI port on multi-output setups (relevant for RPi5/Wayland).
  This is upstream's in-app display blanking layer, independent of this
  fork's external PIR/GPIO/CEC hard-switch approach in `pir_manager.py` — not
  a direct replacement, but worth knowing it exists.
- **Touch/mouse UX rework** in `interface_peripherals.py`: touch handling
  unified into the mouse path, narrower back/next hit-zones (screen/2 ->
  screen/8), pointer auto-hide after `menu_autohide_tm`, menu visibility
  driven by movement instead of y-position.
- **model.py**: retries 5x with 0.5s sleep before showing "no pictures" on a
  fresh/large cache. This fork shows the placeholder immediately, so it can
  flash briefly on startup.
- `start.py` still has upstream's first-run scaffolding (`create_config`,
  `copy_files`, `check_packages` writing to `~/picframe_data`), which this
  fork replaced with a single fixed repo-root `configuration.yaml`. This is a
  deliberate deployment-model difference for this fork, not a gap to close.

### This fork has, upstream doesn't (confirmed against the diff)

- Ken Burns tuning: `kenburns_zoom_pct`, `kenburns_zoom_direction`,
  `kenburns_scroll_direction`, `kenburns_random_pan`,
  `kenburns_landscape_wobble_pct`, `kenburns_portrait_wobble_pct`,
  `kenburns_portrait_border_pct`, `crop_to_aspect_ratio`, and
  `viewer_display.py`'s `__calculate_kenburns_transform`/
  `__apply_kenburns_transform` plus panorama-mode handling.
- Video-as-slideshow preprocessing (`video_extractor.py`, ffmpeg-based
  `FFmpegStreamer` in `video_streamer.py`) as the alternative to mpv
  full-restart playback (`_play_video_subprocess`,
  `play_video`/`play_video_slideshow` in `viewer_display.py`) — the two
  "mutually exclusive strategies" described in `CLAUDE.md`.
- PIR/GPIO/CEC display power management as a fully separate process
  (`scripts/pir_manager.py`, `scripts/test_pir.py`) — not part of upstream's
  package at all.
- SMB photo sync (`scripts/sync_photos.sh`, `scripts/sync_config.yaml`) with
  auto-trigger-on-empty-cache logic in `model.py`.
- Status icon overlay system: `__draw_icon`, `icon_path`/
  `icon_wdt_offset_pct`/`icon_hgt_offset_pct`/`icon_opacity` config, plus the
  icon assets themselves (sync/offline/nowlan/cloud/download/eject/pause/
  play/record/seek/skip/stop pngs) — upstream has none of this.
- `group_by_dir` album-batch playlist mode with
  `~/picframe/shown_albums.log` resume-after-crash/video-restart bookmark,
  `playlist_max_albums`/`playlist_max_files` limits, `delete_after_show`.
- `background`/`solid_background` split (upstream has a single `background`
  key), custom `yuv.fs`/`yuv.vs` shaders, TTY console styling
  (`scripts/set_tty_color.sh`), ffprobe-based video metadata in
  `image_cache.py`/`model.py` (`ffprobe_path`, `delete_file_from_db`).

### Overlapping/conflicting areas (would need manual reconciliation on any future merge)

- **controller.py**: upstream's and this fork's versions have diverged in
  structure (this fork's video-restart logic lives inline in `loop()`/
  `start()`; upstream delegates video logic to viewer methods). Not a simple
  patch-apply — would mean deciding whether to adopt upstream's in-process
  video model wholesale, or just hand-port the missing property wrappers (see
  bug above).
- **model.py `DEFAULT_CONFIG`**: both sides added/removed enough keys (fork:
  `group_by_dir`/Ken Burns tuning/`video_slideshow`/icon config; upstream:
  `text_x_margin`/`display_hdmi`/`generate_random_string`) that a straight
  merge of this dict would conflict on nearly every line.
- **geo_reverse.py**: upstream changed the constructor signature
  (`GeoReverse(load_geoloc, geo_key, ...)` vs. this fork's
  `GeoReverse(geo_key, ...)`) — adopting the Nominatim compliance fix
  requires updating the call site in `model.py`.
- **video_player.py**: same filename, completely different purpose on each
  side (upstream: VLC playback subprocess; fork: OpenCV raw-frame streamer
  for `video_streamer.py`'s `FFmpegStreamer`) — pure naming collision, no
  shared code.
- **get_image_meta.py**: upstream's XMP/IPTC refactor and this fork's
  `get_video_info` addition both touch the same module; adopting upstream's
  metadata refactor means re-adding the fork's video-info function on top.
