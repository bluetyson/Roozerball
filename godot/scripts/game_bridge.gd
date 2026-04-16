## GameBridge — Autoloaded singleton that communicates with the Python engine.
##
## Launches the Python process, sends commands as JSON, and receives
## game-state snapshots back.  All other scripts read from
## ``GameBridge.state`` to render the scene.
extends Node

# ── signals ──────────────────────────────────────────────────────────
signal state_updated(snapshot: Dictionary)
signal phase_result_received(result: Dictionary)
signal game_over(winner: String)
signal bridge_error(message: String)
signal engine_ready

# ── configuration ────────────────────────────────────────────────────
## Path to Python executable; override with --python=<path> on cmdline.
var python_path: String = "python"
## Repo root is one directory up from the godot/ folder.
var repo_root: String = ""

# ── runtime state ────────────────────────────────────────────────────
var state: Dictionary = {}
var is_ready: bool = false
var _pid: int = -1
var _stdin: FileAccess = null
var _stdout: FileAccess = null
var _bridge_thread: Thread = null
var _pipe_path_in: String = ""
var _pipe_path_out: String = ""
var _poll_timer: Timer = null

# Queued commands waiting for engine readiness.
var _command_queue: Array[Dictionary] = []


func _ready() -> void:
	repo_root = ProjectSettings.globalize_path("res://").get_base_dir()
	# If running from the godot/ subfolder the repo root is one level up.
	if repo_root.ends_with("/godot") or repo_root.ends_with("\\godot"):
		repo_root = repo_root.get_base_dir()

	_start_bridge()


func _start_bridge() -> void:
	# Use temp files for communication (cross-platform).
	var tmp = OS.get_user_data_dir()
	_pipe_path_in = tmp.path_join("roozerball_cmd.json")
	_pipe_path_out = tmp.path_join("roozerball_state.json")

	# Clear old files.
	if FileAccess.file_exists(_pipe_path_in):
		DirAccess.remove_absolute(_pipe_path_in)
	if FileAccess.file_exists(_pipe_path_out):
		DirAccess.remove_absolute(_pipe_path_out)

	# Launch the Python bridge process.
	var script_path = repo_root.path_join("roozerball").path_join("godot_bridge.py")
	var args: PackedStringArray = [
		script_path,
		"--cmd-file", _pipe_path_in,
		"--state-file", _pipe_path_out,
	]

	# Try python3 first (Linux/Mac), then python (Windows or aliased).
	_pid = -1
	for py in ["python3", "python"]:
		_pid = OS.create_process(py, args)
		if _pid > 0:
			python_path = py
			break

	if _pid <= 0:
		var msg := "Cannot find Python 3 — install Python 3.11+ and ensure 'python3' or 'python' is on PATH."
		bridge_error.emit(msg)
		push_error("GameBridge: " + msg)
		return

	# Poll for the initial state file from the Python process.
	_poll_timer = Timer.new()
	_poll_timer.wait_time = 0.1
	_poll_timer.one_shot = false
	_poll_timer.timeout.connect(_poll_for_ready)
	add_child(_poll_timer)
	_poll_timer.start()


func _poll_for_ready() -> void:
	if FileAccess.file_exists(_pipe_path_out):
		var content = FileAccess.get_file_as_string(_pipe_path_out)
		if content.length() > 0:
			var json = JSON.new()
			if json.parse(content) == OK:
				state = json.data
				is_ready = true
				_poll_timer.stop()
				_poll_timer.queue_free()
				_poll_timer = null
				engine_ready.emit()
				state_updated.emit(state)
				# Flush queued commands.
				for cmd in _command_queue:
					_send_command(cmd)
				_command_queue.clear()


# ── public API ───────────────────────────────────────────────────────

## Advance one phase and return the phase result.
func advance_phase() -> void:
	_send_or_queue({"action": "advance_phase"})


## Play a full turn (6 phases).
func play_turn() -> void:
	_send_or_queue({"action": "play_turn"})


## Start a new game.
func new_game(home_name: String = "Home", visitor_name: String = "Visitor") -> void:
	_send_or_queue({"action": "new_game", "home": home_name, "visitor": visitor_name})


## Request the full board state (figures + positions).
func request_board_state() -> void:
	_send_or_queue({"action": "board_state"})


# ── internal ─────────────────────────────────────────────────────────

func _send_or_queue(cmd: Dictionary) -> void:
	if is_ready:
		_send_command(cmd)
	else:
		_command_queue.append(cmd)


func _send_command(cmd: Dictionary) -> void:
	# Write command JSON to the command file.
	var f = FileAccess.open(_pipe_path_in, FileAccess.WRITE)
	if f == null:
		bridge_error.emit("Cannot write command file")
		return
	f.store_string(JSON.stringify(cmd))
	f.close()

	# Wait for the Python side to write back a response.
	await _wait_for_response()


func _wait_for_response() -> void:
	# Poll up to 10 seconds for a fresh state file.
	var deadline = Time.get_ticks_msec() + 10_000
	var old_turn = state.get("turn", -1)
	var old_phase = state.get("phase", "")
	while Time.get_ticks_msec() < deadline:
		await get_tree().create_timer(0.05).timeout
		if not FileAccess.file_exists(_pipe_path_out):
			continue
		var content = FileAccess.get_file_as_string(_pipe_path_out)
		if content.length() == 0:
			continue
		var json = JSON.new()
		if json.parse(content) != OK:
			continue
		var new_state: Dictionary = json.data
		# Check if the state actually changed.
		if new_state.get("_seq", 0) != state.get("_seq", 0):
			state = new_state
			state_updated.emit(state)
			if state.get("game_over", false):
				var scores = state.get("scores", {})
				var winner = ""
				var best = -1
				for team_name in scores:
					if scores[team_name] > best:
						best = scores[team_name]
						winner = team_name
				game_over.emit(winner)
			if state.has("phase_result"):
				phase_result_received.emit(state["phase_result"])
			return
	bridge_error.emit("Timeout waiting for engine response")


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		_cleanup()


func _cleanup() -> void:
	if _pid > 0:
		OS.kill(_pid)
		_pid = -1
	# Clean up temp files.
	for path in [_pipe_path_in, _pipe_path_out]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(path)
