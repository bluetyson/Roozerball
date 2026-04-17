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
## Fired during connection to report progress / diagnostic messages.
signal engine_status(message: String)

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
var _preflight_thread: Thread = null
var _pipe_path_in: String = ""
var _pipe_path_out: String = ""
var _error_log_path: String = ""
var _poll_timer: Timer = null
var _script_path: String = ""
var _connect_start_msec: int = 0
const CONNECT_TIMEOUT_MS: int = 15_000  # 15 seconds before giving up
# Set to true once Python writes its _bridge_starting indicator.
var _python_alive: bool = false

# Queued commands waiting for engine readiness.
var _command_queue: Array[Dictionary] = []


func _ready() -> void:
	repo_root = ProjectSettings.globalize_path("res://").get_base_dir()
	# If running from the godot/ subfolder the repo root is one level up.
	if repo_root.ends_with("/godot") or repo_root.ends_with("\\godot"):
		repo_root = repo_root.get_base_dir()

	# Allow --python=<path> on the command line to override the interpreter.
	for arg in OS.get_cmdline_args():
		if arg.begins_with("--python="):
			python_path = arg.substr(9)  # skip "--python="
			break

	_start_bridge()


func _start_bridge() -> void:
	# Use temp files for communication (cross-platform).
	var tmp = OS.get_user_data_dir()
	_pipe_path_in = tmp.path_join("roozerball_cmd.json")
	_pipe_path_out = tmp.path_join("roozerball_state.json")
	_error_log_path = tmp.path_join("roozerball_error.log")

	# Clear old files.
	for old_path in [_pipe_path_in, _pipe_path_out, _error_log_path]:
		if FileAccess.file_exists(old_path):
			DirAccess.remove_absolute(old_path)

	# Validate the bridge script exists before trying to launch it.
	_script_path = repo_root.path_join("roozerball").path_join("godot_bridge.py")
	if not FileAccess.file_exists(_script_path):
		var msg := (
			"Python bridge script not found:\n  %s\n\n" % _script_path
			+ "Resolved repo root: %s\n" % repo_root
			+ "Ensure the Godot project is inside the repository's 'godot/' folder."
		)
		bridge_error.emit(msg)
		push_error("GameBridge: " + msg)
		return

	engine_status.emit("Script: %s\nCmd file: %s\nState file: %s" % [_script_path, _pipe_path_in, _pipe_path_out])
	engine_status.emit("Running pre-flight Python check…")

	# ── Run pre-flight in a background thread ───────────────────────
	# OS.execute() is blocking: running it on the main thread would
	# freeze Godot's entire render/event loop (including timers) for
	# as long as Python takes to start — several seconds on conda /
	# pyenv / Windows environments.  A background Thread keeps the UI
	# responsive while we wait.
	_pid = -1
	_preflight_thread = Thread.new()
	_preflight_thread.start(_run_preflight)


# Background thread: discovers a working Python executable and verifies
# the engine is importable.  Uses call_deferred() for all UI updates so
# that no Godot node is touched from outside the main thread.
func _run_preflight() -> void:
	var is_windows: bool = OS.get_name() == "Windows"

	# ── Build ordered list of Python executables to try ───────────────
	var candidates: PackedStringArray = PackedStringArray()

	# 1. Explicit --python= override (set in _ready from CLI) takes priority.
	if python_path != "python":
		candidates.append(python_path)

	# 2. Standard names that should be on PATH in most environments.
	candidates.append("python3")
	candidates.append("python")
	if is_windows:
		candidates.append("py")  # Windows Python Launcher.

	# 3. Python from an active virtual-environment (VIRTUAL_ENV).
	var venv := OS.get_environment("VIRTUAL_ENV")
	if venv != "":
		if is_windows:
			candidates.append(venv.path_join("Scripts/python.exe"))
		else:
			candidates.append(venv.path_join("bin/python3"))

	# 4. Python from an active conda environment (CONDA_PREFIX).
	var conda_prefix := OS.get_environment("CONDA_PREFIX")
	if conda_prefix != "":
		if is_windows:
			candidates.append(conda_prefix.path_join("python.exe"))
		else:
			candidates.append(conda_prefix.path_join("bin/python3"))

	# 5. Conda 'roozerball' environment at common installation prefixes.
	var home: String
	if is_windows:
		home = OS.get_environment("USERPROFILE")
	else:
		home = OS.get_environment("HOME")
	if home != "":
		var bases := PackedStringArray([
			"miniconda3", "miniconda", "anaconda3", "anaconda",
			"mambaforge", "miniforge3",
		])
		for base in bases:
			var env_py: String
			if is_windows:
				env_py = home.path_join(base + "/envs/roozerball/python.exe")
			else:
				env_py = home.path_join(base + "/envs/roozerball/bin/python3")
			if not candidates.has(env_py):
				candidates.append(env_py)

	# ── Try each candidate in order ────────────────────────────────────
	var preflight_py := ""
	for py in candidates:
		# For absolute paths skip the OS.execute() call if the file is
		# missing — avoids spurious NUL-byte output Godot warns about
		# when the OS tries to execute a non-existent binary.
		if py.is_absolute_path() and not FileAccess.file_exists(py):
			continue
		var check_output: Array = []
		var check_code := OS.execute(py, ["-c", "import sys; v=sys.version_info; print('%d.%d.%d'%(v.major,v.minor,v.micro))"], check_output, false)
		if check_code == 0:
			var version_str := ""
			if check_output.size() > 0:
				version_str = check_output[0].strip_edges()
			preflight_py = py
			call_deferred(
				"_emit_engine_status",
				"Found: %s%s" % [py, (" → " + version_str) if version_str != "" else ""]
			)
			break

	if preflight_py == "":
		call_deferred(
			"_on_preflight_done",
			{
				"success": false,
				"error": (
					"Cannot find Python 3 — install Python 3.11+ and ensure "
					+ "the interpreter is on PATH.\n\n"
					+ "Tried:\n  • " + "\n  • ".join(candidates) + "\n\n"
					+ "Tips:\n"
					+ "  • Activate your conda environment before launching Godot:\n"
					+ "        conda activate roozerball\n"
					+ "  • Or pass --python=<path> as a command-line argument."
				),
			}
		)
		return

	# Verify the engine is importable (catches missing deps / syntax errors
	# immediately with full output instead of the background-process black hole).
	var import_snippet := (
		"import sys; sys.path.insert(0, %s); "
		% _python_repr(repo_root)
		+ "from roozerball.engine.game import Game; print('engine OK')"
	)
	call_deferred("_emit_engine_status", "Checking engine import…")
	var import_output: Array = []
	var import_code := OS.execute(preflight_py, ["-c", import_snippet], import_output, true)
	if import_code != 0:
		var detail := (
			"\n".join(import_output).strip_edges()
			if import_output.size() > 0
			else "(no output)"
		)
		call_deferred(
			"_on_preflight_done",
			{
				"success": false,
				"error": (
					"Python can start but cannot import the game engine.\n\n"
					+ "Command: %s -c \"%s\"\n" % [preflight_py, import_snippet]
					+ "Exit code: %d\n\nOutput:\n%s\n\n" % [import_code, detail]
					+ "Repo root: %s\nScript: %s" % [repo_root, _script_path]
				),
			}
		)
		return

	call_deferred(
		"_on_preflight_done",
		{"success": true, "python_path": preflight_py}
	)


# Thread-safe helper: emits engine_status from the main thread.
func _emit_engine_status(msg: String) -> void:
	engine_status.emit(msg)


# Called on the main thread when the preflight thread finishes.
func _on_preflight_done(result: Dictionary) -> void:
	if _preflight_thread:
		_preflight_thread.wait_to_finish()
		_preflight_thread = null

	if not result.get("success", false):
		var msg: String = result.get("error", "Unknown pre-flight error")
		bridge_error.emit(msg)
		push_error("GameBridge: " + msg)
		return

	python_path = result["python_path"]
	engine_status.emit("Pre-flight OK — engine is importable")
	_launch_bridge_process()


# Launch the Python bridge process and start the state-file polling timer.
func _launch_bridge_process() -> void:
	var args: PackedStringArray = [
		_script_path,
		"--cmd-file", _pipe_path_in,
		"--state-file", _pipe_path_out,
		"--error-file", _error_log_path,
	]

	engine_status.emit("Launching '%s'…" % python_path)
	_pid = OS.create_process(python_path, args)
	if _pid <= 0:
		var msg := (
			"OS.create_process() failed for '%s'.\nArgs: %s" % [python_path, str(args)]
		)
		bridge_error.emit(msg)
		push_error("GameBridge: " + msg)
		return

	engine_status.emit("Launched '%s' (PID %d)\nWaiting for engine to start…" % [python_path, _pid])

	# Poll for the initial state file from the Python process.
	_connect_start_msec = Time.get_ticks_msec()
	_poll_timer = Timer.new()
	_poll_timer.wait_time = 0.1
	_poll_timer.one_shot = false
	_poll_timer.timeout.connect(_poll_for_ready)
	add_child(_poll_timer)
	_poll_timer.start()


func _poll_for_ready() -> void:
	var elapsed_ms := Time.get_ticks_msec() - _connect_start_msec
	var elapsed_s := elapsed_ms / 1000.0

	# Check the state file FIRST — Python may have written a startup-error payload
	# and then exited.  Reading the file here lets us show the real Python traceback
	# instead of the generic "process exited unexpectedly" message below.
	if FileAccess.file_exists(_pipe_path_out):
		var content = FileAccess.get_file_as_string(_pipe_path_out)
		if content.length() > 0:
			var json = JSON.new()
			if json.parse(content) == OK:
				var parsed: Dictionary = json.data
				# Startup error written by godot_bridge.py before crashing.
				if parsed.has("_startup_error"):
					_poll_timer.stop()
					_poll_timer.queue_free()
					_poll_timer = null
					var tb: String = parsed.get("_startup_traceback", "").strip_edges()
					var full_msg := "Python engine startup error:\n" + str(parsed["_startup_error"])
					if tb != "":
						full_msg += "\n" + tb
					bridge_error.emit(full_msg)
					return
				# Early "alive" indicator written by godot_bridge.py before Game() init.
				if parsed.has("_bridge_starting"):
					if not _python_alive:
						_python_alive = true
						engine_status.emit("Python started — game engine initializing…")
					return  # Keep polling; engine not ready yet.
				state = parsed
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
				return

	# Detect if the Python process has already exited unexpectedly (checked after
	# the state-file read above so a Python-written error payload takes priority).
	if _pid > 0 and not OS.is_process_running(_pid):
		_poll_timer.stop()
		_poll_timer.queue_free()
		_poll_timer = null

		# Try to read the dedicated error log (Python redirects stderr there
		# and also writes full tracebacks on unhandled exceptions).
		var error_detail := ""
		if _error_log_path != "" and FileAccess.file_exists(_error_log_path):
			error_detail = FileAccess.get_file_as_string(_error_log_path).strip_edges()

		var msg := "Python process exited unexpectedly (PID %d) after %.1f s.\n" % [_pid, elapsed_s]
		if error_detail != "":
			msg += "\nPython error output:\n" + error_detail + "\n"
		else:
			msg += "No error log was written — the process may have been killed externally.\n"
		msg += "\nScript: %s" % _script_path
		bridge_error.emit(msg)
		return

	# Enforce a connection timeout.
	if elapsed_ms >= CONNECT_TIMEOUT_MS:
		_poll_timer.stop()
		_poll_timer.queue_free()
		_poll_timer = null

		# Kill the hung process so its stderr (redirected to the error file)
		# is flushed before we try to read it.
		if _pid > 0 and OS.is_process_running(_pid):
			OS.kill(_pid)

		# Read whatever diagnostic output Python managed to write.
		var error_detail := ""
		if _error_log_path != "" and FileAccess.file_exists(_error_log_path):
			error_detail = FileAccess.get_file_as_string(_error_log_path).strip_edges()

		var hint := (
			"Python started successfully but the game engine never initialised.\n"
			if _python_alive
			else "Python did not write any startup indicator within the timeout.\n"
		)
		var msg := (
			"Timed out after %.0f s waiting for Python engine.\n" % elapsed_s
			+ hint
			+ "Script:     %s\n" % _script_path
			+ "State file: %s\n" % _pipe_path_out
		)
		if error_detail != "":
			msg += "\nPython output / traceback:\n" + error_detail
		else:
			msg += (
				"\nNo error output captured.\n"
				+ "To diagnose, run Python manually:\n"
				+ "  %s %s --cmd-file /tmp/rz_cmd.json --state-file /tmp/rz_state.json"
				% [python_path if python_path != "" else "python3", _script_path]
			)
		bridge_error.emit(msg)
		return

	# Emit a progress update once per second.
	# (Skip the first 200 ms to avoid a flash before the PID message is shown.)
	var last_s := int((elapsed_ms - 100) / 1000)  # 100 ms = half the poll interval
	var cur_s := int(elapsed_ms / 1000)
	if cur_s != last_s and elapsed_ms > 200:
		engine_status.emit("Waiting for Python engine… %.0f s" % elapsed_s)


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
	# Wait for the preflight thread to finish (if still running) before
	# tearing down the node, otherwise GDScript will assert.
	if _preflight_thread and _preflight_thread.is_started():
		_preflight_thread.wait_to_finish()
	_preflight_thread = null
	if _pid > 0:
		OS.kill(_pid)
		_pid = -1
	# Clean up temp files.
	for path in [_pipe_path_in, _pipe_path_out, _error_log_path]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(path)


## Strip NUL bytes from *s* and trim surrounding whitespace.
## OS.execute() can capture NUL-padded output on some platforms; passing
## those strings through Godot's text system triggers Unicode parse warnings.
static func _strip_output(s: String) -> String:
	return s.replace(char(0), "").strip_edges()


## Return a Python repr()-style string literal for embedding in -c snippets.
## Escapes backslashes, quotes, and control characters that could break the
## string context.
static func _python_repr(s: String) -> String:
	var out := s
	out = out.replace("\\", "\\\\")
	out = out.replace("'", "\\'")
	out = out.replace("\n", "\\n")
	out = out.replace("\r", "\\r")
	out = out.replace("\t", "\\t")
	out = out.replace(char(0), "\\0")
	return "'" + out + "'"
