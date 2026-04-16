## HUD — 2D overlay showing scoreboard, phase indicator, game log,
## and penalty-box display on top of the 3D arena.
extends CanvasLayer

# ── node references (created in _ready) ──────────────────────────────
var _scoreboard_label: Label = null
var _phase_label: Label = null
var _log_box: RichTextLabel = null
var _controls_label: Label = null
var _penalty_panel: VBoxContainer = null
var _auto_indicator: Label = null
var _bridge_status_label: Label = null

# Style constants.
const PANEL_BG := Color(0.05, 0.05, 0.12, 0.85)
const ACCENT := Color(0.92, 0.27, 0.38)
const TEXT_COLOR := Color(0.92, 0.92, 0.95)
const HOME_COLOR := Color(0.3, 0.6, 1.0)
const VISITOR_COLOR := Color(1.0, 0.3, 0.3)


func _ready() -> void:
	layer = 1
	_build_ui()

	# Connect to GameBridge signals.
	if GameBridge:
		GameBridge.state_updated.connect(_on_state_updated)
		GameBridge.bridge_error.connect(_on_bridge_error)
		GameBridge.engine_ready.connect(_on_engine_ready)


func _build_ui() -> void:
	# ── Scoreboard (top-centre) ──────────────────────────────────────
	var score_panel := _make_panel(Vector2(660, 10), Vector2(600, 90))
	_scoreboard_label = Label.new()
	_scoreboard_label.text = "HOME 0 — 0 VISITOR"
	_scoreboard_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_scoreboard_label.add_theme_font_size_override("font_size", 28)
	_scoreboard_label.add_theme_color_override("font_color", TEXT_COLOR)
	_scoreboard_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	score_panel.add_child(_scoreboard_label)
	add_child(score_panel)

	# ── Phase indicator (top-left) ───────────────────────────────────
	var phase_panel := _make_panel(Vector2(10, 10), Vector2(350, 80))
	_phase_label = Label.new()
	_phase_label.text = "Phase: Setup"
	_phase_label.add_theme_font_size_override("font_size", 20)
	_phase_label.add_theme_color_override("font_color", ACCENT)
	_phase_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	phase_panel.add_child(_phase_label)
	add_child(phase_panel)

	# ── Game log (bottom-left) ───────────────────────────────────────
	var log_panel := _make_panel(Vector2(10, 600), Vector2(550, 460))
	_log_box = RichTextLabel.new()
	_log_box.bbcode_enabled = true
	_log_box.scroll_following = true
	_log_box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_log_box.add_theme_font_size_override("normal_font_size", 14)
	_log_box.add_theme_color_override("default_color", TEXT_COLOR)
	log_panel.add_child(_log_box)
	add_child(log_panel)

	# ── Penalty box (right side) ─────────────────────────────────────
	var penalty_container := _make_panel(Vector2(1560, 110), Vector2(350, 400))
	var penalty_title := Label.new()
	penalty_title.text = "⏱ Penalty Box"
	penalty_title.add_theme_font_size_override("font_size", 18)
	penalty_title.add_theme_color_override("font_color", ACCENT)
	penalty_container.add_child(penalty_title)
	_penalty_panel = VBoxContainer.new()
	_penalty_panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_penalty_panel.offset_top = 30
	penalty_container.add_child(_penalty_panel)
	add_child(penalty_container)

	# ── Controls help (bottom-right) ─────────────────────────────────
	var ctrl_panel := _make_panel(Vector2(1560, 900), Vector2(350, 160))
	_controls_label = Label.new()
	_controls_label.text = (
		"[Space] Advance phase\n"
		+ "[T] Play full turn\n"
		+ "[A] Toggle auto-play\n"
		+ "[1] Overhead  [2] Trackside  [3] Goal-cam"
	)
	_controls_label.add_theme_font_size_override("font_size", 14)
	_controls_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.7))
	_controls_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ctrl_panel.add_child(_controls_label)
	add_child(ctrl_panel)

	# ── Auto-play indicator ──────────────────────────────────────────
	_auto_indicator = Label.new()
	_auto_indicator.text = ""
	_auto_indicator.add_theme_font_size_override("font_size", 22)
	_auto_indicator.add_theme_color_override("font_color", Color(0.2, 1.0, 0.3))
	_auto_indicator.position = Vector2(380, 20)
	add_child(_auto_indicator)

	# ── Bridge status indicator ──────────────────────────────────────
	_bridge_status_label = Label.new()
	_bridge_status_label.text = "⏳ Connecting to Python engine..."
	_bridge_status_label.add_theme_font_size_override("font_size", 16)
	_bridge_status_label.add_theme_color_override("font_color", Color(1.0, 0.7, 0.2))
	_bridge_status_label.position = Vector2(660, 110)
	add_child(_bridge_status_label)


# ── state update ─────────────────────────────────────────────────────

func _on_state_updated(state: Dictionary) -> void:
	_update_scoreboard(state)
	_update_phase(state)
	_update_log(state)
	_update_penalty_box(state)


func _update_scoreboard(state: Dictionary) -> void:
	var scores: Dictionary = state.get("scores", {})
	var home_name := ""
	var visitor_name := ""
	var home_score := 0
	var visitor_score := 0

	var ht: Dictionary = state.get("home_team", {})
	var vt: Dictionary = state.get("visitor_team", {})
	home_name = ht.get("name", "Home")
	visitor_name = vt.get("name", "Visitor")

	for team_name in scores:
		if team_name == home_name:
			home_score = scores[team_name]
		else:
			visitor_score = scores[team_name]

	var period: int = state.get("period", 1)
	var time_rem: int = state.get("time_remaining", 20)

	if _scoreboard_label:
		_scoreboard_label.text = "%s  %d  —  %d  %s\nPeriod %d  |  %d:00" % [
			home_name, home_score, visitor_score, visitor_name, period, time_rem
		]


func _update_phase(state: Dictionary) -> void:
	if _phase_label == null:
		return
	var phase: String = state.get("phase", "setup")
	var turn: int = state.get("turn", 0)
	var init_sector = state.get("initiative_sector")
	var sector_str := ""
	if init_sector != null and init_sector is int and init_sector >= 0:
		var names := ["A","B","C","D","E","F","G","H","I","J","K","L"]
		if init_sector < names.size():
			sector_str = "  (Sector %s)" % names[init_sector]
	_phase_label.text = "Turn %d  |  Phase: %s%s" % [turn, phase.to_upper(), sector_str]

	if state.get("game_over", false):
		_phase_label.text += "\n🏁 GAME OVER"


func _update_log(state: Dictionary) -> void:
	if _log_box == null:
		return
	var log_lines: Array = state.get("log", [])
	_log_box.clear()
	for line in log_lines:
		var s: String = str(line)
		if "Goal!" in s or "GOAL" in s:
			_log_box.append_text("[color=#ffcc00]%s[/color]\n" % s)
		elif "Brawl" in s or "Swoop" in s or "Combat" in s:
			_log_box.append_text("[color=#ff6666]%s[/color]\n" % s)
		elif "Cannon" in s or "fired" in s:
			_log_box.append_text("[color=#ff8833]%s[/color]\n" % s)
		elif "Penalty" in s:
			_log_box.append_text("[color=#ff4444]%s[/color]\n" % s)
		else:
			_log_box.append_text("%s\n" % s)


func _update_penalty_box(state: Dictionary) -> void:
	if _penalty_panel == null:
		return
	# Clear old entries.
	for child in _penalty_panel.get_children():
		child.queue_free()

	var pbox: Dictionary = state.get("penalty_box", {})
	for side in ["home", "visitor"]:
		var figures: Array = pbox.get(side, [])
		if figures.size() == 0:
			continue
		var header := Label.new()
		header.text = side.to_upper()
		header.add_theme_font_size_override("font_size", 15)
		header.add_theme_color_override("font_color", HOME_COLOR if side == "home" else VISITOR_COLOR)
		_penalty_panel.add_child(header)
		for fig in figures:
			var entry := Label.new()
			entry.text = "  %s (%s)" % [fig.get("name", "?"), fig.get("type", "?")]
			entry.add_theme_font_size_override("font_size", 13)
			entry.add_theme_color_override("font_color", TEXT_COLOR)
			_penalty_panel.add_child(entry)


func set_auto_play(enabled: bool) -> void:
	if _auto_indicator:
		_auto_indicator.text = "▶ AUTO" if enabled else ""


func set_bridge_status(connected: bool, error_msg: String = "") -> void:
	if _bridge_status_label == null:
		return
	if connected:
		_bridge_status_label.text = ""
	elif error_msg != "":
		_bridge_status_label.text = "⚠ " + error_msg
		_bridge_status_label.add_theme_color_override("font_color", Color(1.0, 0.3, 0.3))
	else:
		_bridge_status_label.text = "⏳ Connecting to Python engine..."
		_bridge_status_label.add_theme_color_override("font_color", Color(1.0, 0.7, 0.2))


func _on_bridge_error(message: String) -> void:
	set_bridge_status(false, message)


func _on_engine_ready() -> void:
	set_bridge_status(true)


# ── helpers ──────────────────────────────────────────────────────────

func _make_panel(pos: Vector2, size: Vector2) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.position = pos
	panel.size = size
	var style := StyleBoxFlat.new()
	style.bg_color = PANEL_BG
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_left = 8
	style.corner_radius_bottom_right = 8
	style.border_width_top = 1
	style.border_color = Color(1, 1, 1, 0.1)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	panel.add_theme_stylebox_override("panel", style)
	return panel
