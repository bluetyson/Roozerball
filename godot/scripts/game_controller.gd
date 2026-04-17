## GameController — Main scene script that wires the arena, figures,
## ball, camera and HUD together.  Listens for engine state updates
## from GameBridge and refreshes all visual components.
extends Node3D

# ── child nodes (created in _ready) ─────────────────────────────────
var arena: ArenaBuilder = null
var figures: FigureManager = null
var ball: BallVisual = null
var camera_rig: CameraRig = null
var hud: CanvasLayer = null
var atmosphere: StadiumAtmosphere = null

# ── auto-play ────────────────────────────────────────────────────────
var auto_play := false
var _auto_timer: Timer = null
const AUTO_INTERVAL := 0.6  # seconds between auto-advance


func _ready() -> void:
	# Build the arena.
	arena = ArenaBuilder.new()
	arena.name = "Arena"
	add_child(arena)
	arena.build()

	# Stadium atmosphere (crowd, labels, particles).
	atmosphere = StadiumAtmosphere.new()
	atmosphere.name = "Atmosphere"
	add_child(atmosphere)
	atmosphere.build()

	# Figure manager.
	figures = FigureManager.new()
	figures.name = "Figures"
	figures.arena = arena
	add_child(figures)

	# Ball.
	ball = BallVisual.new()
	ball.name = "Ball"
	ball.arena = arena
	add_child(ball)

	# Camera.
	camera_rig = CameraRig.new()
	camera_rig.name = "CameraRig"
	add_child(camera_rig)

	# Lighting.
	_setup_lighting()

	# HUD.
	hud = load("res://scripts/hud.gd").new()
	hud.name = "HUD"
	add_child(hud)

	# Auto-play timer.
	_auto_timer = Timer.new()
	_auto_timer.wait_time = AUTO_INTERVAL
	_auto_timer.one_shot = false
	_auto_timer.timeout.connect(_on_auto_tick)
	add_child(_auto_timer)

	# Connect bridge signals.
	if GameBridge:
		GameBridge.state_updated.connect(_on_state_updated)
		GameBridge.game_over.connect(_on_game_over)
		GameBridge.engine_ready.connect(_on_engine_ready)
		GameBridge.bridge_error.connect(_on_bridge_error)


func _on_engine_ready() -> void:
	print("Engine ready — requesting initial board state")
	GameBridge.request_board_state()


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("advance_phase"):
		GameBridge.advance_phase()
	elif event.is_action_pressed("play_turn"):
		GameBridge.play_turn()
	elif event.is_action_pressed("toggle_auto"):
		auto_play = not auto_play
		if auto_play:
			_auto_timer.start()
		else:
			_auto_timer.stop()
		if hud.has_method("set_auto_play"):
			hud.set_auto_play(auto_play)


func _on_auto_tick() -> void:
	if not GameBridge.state.get("game_over", false):
		GameBridge.advance_phase()
	else:
		auto_play = false
		_auto_timer.stop()
		if hud.has_method("set_auto_play"):
			hud.set_auto_play(false)


# ── state sync ───────────────────────────────────────────────────────

func _on_state_updated(state: Dictionary) -> void:
	# Update figures.
	var board_data: Array = state.get("board", [])
	var home_team: Dictionary = state.get("home_team", {})
	var visitor_team: Dictionary = state.get("visitor_team", {})
	figures.update_from_state(board_data, home_team, visitor_team)

	# Update ball.
	var ball_data: Dictionary = state.get("ball", {})
	ball.update_from_state(ball_data)

	# Camera focus: follow the ball carrier or ball sector.
	var ball_sector = ball_data.get("sector_index", -1)
	if ball_sector is int and ball_sector >= 0:
		camera_rig.focus_sector = ball_sector

	# Flash goal effect.
	if state.has("phase_result"):
		var pr: Dictionary = state["phase_result"]
		if pr.has("messages"):
			for msg in pr["messages"]:
				if "GOAL" in str(msg) or "Goal!" in str(msg):
					_flash_goal_effect()


func _on_game_over(winner: String) -> void:
	print("Game over — winner: ", winner)
	auto_play = false
	_auto_timer.stop()


func _on_bridge_error(message: String) -> void:
	push_warning("Bridge error: " + message)
	if hud and hud.has_method("set_bridge_status"):
		hud.set_bridge_status(false, message)


# ── lighting ─────────────────────────────────────────────────────────

func _setup_lighting() -> void:
	# Ambient light.
	var env := WorldEnvironment.new()
	env.name = "WorldEnv"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.04, 0.04, 0.08)
	# Use AMBIENT_SOURCE_COLOR so the ambient_light_color is actually applied.
	# The default AMBIENT_SOURCE_BG uses the background colour (nearly black),
	# which makes all arena surfaces invisible against the dark backdrop.
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.55, 0.55, 0.65)
	environment.ambient_light_energy = 1.2
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	environment.glow_enabled = true
	environment.glow_intensity = 0.5
	environment.glow_bloom = 0.3
	environment.fog_enabled = true
	environment.fog_light_color = Color(0.1, 0.1, 0.15)
	environment.fog_density = 0.005
	env.environment = environment
	add_child(env)

	# Overhead key light — strong directional from directly above so the
	# entire arena surface is lit regardless of camera angle.
	var key_light := DirectionalLight3D.new()
	key_light.name = "OverheadKeyLight"
	key_light.rotation_degrees = Vector3(-90, 0, 0)  # straight down
	key_light.light_energy = 2.0
	key_light.light_color = Color(1.0, 0.97, 0.92)
	key_light.shadow_enabled = false
	add_child(key_light)

	# Four floodlights at compass points, high above the arena.
	var floodlight_positions := [
		Vector3(22, 18, 0),
		Vector3(-22, 18, 0),
		Vector3(0, 18, 22),
		Vector3(0, 18, -22),
	]
	for i in range(floodlight_positions.size()):
		var light := SpotLight3D.new()
		light.name = "Floodlight_%d" % i
		light.position = floodlight_positions[i]
		light.look_at(Vector3.ZERO, Vector3.UP)
		light.light_energy = 2.5
		light.light_color = Color(1.0, 0.95, 0.85)
		light.spot_range = 55.0
		light.spot_angle = 50.0
		# Disable shadows on spot lights — shadow maps can cause rendering
		# artefacts with many small procedural meshes in Godot 4.
		light.shadow_enabled = false
		add_child(light)

		# Visible floodlight rig mesh.
		var rig := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = Vector3(1.0, 0.5, 1.0)
		rig.mesh = box
		rig.position = floodlight_positions[i] + Vector3(0, 0.5, 0)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.3, 0.3, 0.35)
		mat.metallic = 0.5
		rig.material_override = mat
		add_child(rig)

	# Directional fill (side/moonlight) to add depth to the banked surfaces.
	var dir_light := DirectionalLight3D.new()
	dir_light.name = "MoonLight"
	dir_light.rotation_degrees = Vector3(-40, 30, 0)
	dir_light.light_energy = 0.8
	dir_light.light_color = Color(0.6, 0.65, 0.8)
	dir_light.shadow_enabled = false
	add_child(dir_light)


# ── effects ──────────────────────────────────────────────────────────

func _flash_goal_effect() -> void:
	# Brief screen flash for a goal scored.
	var flash := ColorRect.new()
	flash.color = Color(1, 1, 0.7, 0.35)
	flash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# Need to add to a CanvasLayer.
	var cl := CanvasLayer.new()
	cl.layer = 10
	cl.add_child(flash)
	add_child(cl)

	var tween := create_tween()
	tween.tween_property(flash, "color:a", 0.0, 0.5)
	tween.tween_callback(cl.queue_free)
