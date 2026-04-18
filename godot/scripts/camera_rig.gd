## CameraRig — Multi-mode camera system for the 3D arena.
##
## Supports five modes:
##   1  Overhead       — top-down view of the full arena
##   2  Trackside      — low-angle rotating view following the action
##   3  Goal-cam       — behind-the-goal view for scoring moments
##   4  Follow Ball    — close-up camera orbiting around the ball
##   5  Follow Player  — close-up camera tracking the ball carrier
##
## Press 1/2/3/4/5 to switch.  The rig smoothly interpolates between views.
## Right-click or middle-mouse drag to orbit/tilt in any non-overhead mode.
class_name CameraRig
extends Node3D

enum Mode { OVERHEAD, TRACKSIDE, GOALCAM, FOLLOW_BALL, FOLLOW_PLAYER }

# ── configuration ────────────────────────────────────────────────────
@export var overhead_height := 32.0
@export var trackside_height := 4.0
@export var trackside_distance := 20.0
@export var goalcam_distance := 5.0
@export var goalcam_height := 3.0
@export var follow_height := 6.0       # Height above target in follow modes.
@export var follow_distance := 9.0     # Horizontal distance in follow ball mode.
@export var follow_close_distance := 5.5  # Horizontal distance in follow player mode.
@export var lerp_speed := 3.5
@export var orbit_speed := 0.15        # rad/s for trackside auto-orbit.
@export var drag_sensitivity := 0.005  # rad per pixel for mouse-drag orbit.
@export var trackside_pitch_scale := 0.35   # How much pitch_offset shifts trackside height.
@export var goalcam_orbit_scale := 0.3      # How strongly horizontal drag rotates goal-cam.
@export var follow_pitch_scale := 0.4       # Pitch offset → height multiplier in follow modes.
@export var follow_player_height_scale := 0.7  # Follow-player base height relative to follow_height.

# ── state ────────────────────────────────────────────────────────────
var current_mode: Mode = Mode.TRACKSIDE
var _orbit_angle := 0.0   # Horizontal orbit angle (all modes).
var _pitch_offset := 0.0  # Vertical tilt from mouse drag (clamped ±1.2 rad).
var _target_pos := Vector3.ZERO
var _target_look := Vector3.ZERO

var _camera: Camera3D = null

# ── mouse drag ───────────────────────────────────────────────────────
var _dragging := false

# ── focus targets ────────────────────────────────────────────────────
## Sector hint used by trackside auto-orbit.
var focus_sector: int = -1

## World-space ball position — updated each tick by GameController.
var ball_world_pos := Vector3.ZERO

## World-space ball-carrier (or selected figure) position — updated by GameController.
var follow_target_pos := Vector3.ZERO


func _ready() -> void:
	_camera = Camera3D.new()
	_camera.name = "Camera"
	_camera.fov = 65.0
	_camera.near = 0.1
	_camera.far = 200.0
	add_child(_camera)
	_camera.make_current()
	# Start at a trackside angle so the banked 3D structure is immediately
	# visible.  Press 1 to switch to overhead, 2 for trackside, 3 for goalcam.
	_orbit_angle = PI * 0.25  # 45° offset so neither goal is dead-centre
	_apply_trackside_instantly()


func _process(delta: float) -> void:
	_handle_input()
	_update_camera_target(delta)

	# Smooth interpolation.
	_camera.global_position = _camera.global_position.lerp(_target_pos, delta * lerp_speed)
	# Guard against degenerate look_at (camera sitting exactly on look target).
	if _camera.global_position.distance_to(_target_look) > 0.05:
		_camera.look_at(_target_look, _look_up_vec())


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT or mb.button_index == MOUSE_BUTTON_MIDDLE:
			_dragging = mb.pressed
	elif event is InputEventMouseMotion and _dragging:
		if current_mode != Mode.OVERHEAD:
			var mm := event as InputEventMouseMotion
			_orbit_angle -= mm.relative.x * drag_sensitivity
			_pitch_offset = clamp(
				_pitch_offset + mm.relative.y * drag_sensitivity,
				-1.2, 1.2
			)


func _look_up_vec() -> Vector3:
	# Overhead mode looks nearly straight down, so Vector3.UP is almost
	# parallel to the view direction and causes a degenerate look_at.
	# Use -Z as the up reference instead, which is always stable.
	return Vector3(0.0, 0.0, -1.0) if current_mode == Mode.OVERHEAD else Vector3.UP


func _handle_input() -> void:
	if Input.is_action_just_pressed("camera_overhead"):
		current_mode = Mode.OVERHEAD
		_pitch_offset = 0.0
	elif Input.is_action_just_pressed("camera_trackside"):
		current_mode = Mode.TRACKSIDE
		_pitch_offset = 0.0
	elif Input.is_action_just_pressed("camera_goalcam"):
		current_mode = Mode.GOALCAM
		_orbit_angle = 0.0
		_pitch_offset = 0.0
	elif Input.is_action_just_pressed("camera_follow_ball"):
		current_mode = Mode.FOLLOW_BALL
		_pitch_offset = 0.0
	elif Input.is_action_just_pressed("camera_follow_player"):
		current_mode = Mode.FOLLOW_PLAYER
		_pitch_offset = 0.0


func _update_camera_target(delta: float) -> void:
	match current_mode:
		Mode.OVERHEAD:
			_target_pos = Vector3(0, overhead_height, 0.1)
			_target_look = Vector3.ZERO
		Mode.TRACKSIDE:
			_orbit_angle += orbit_speed * delta
			if focus_sector >= 0:
				# Bias toward the focus sector.
				var target_angle := focus_sector * (TAU / 12.0) + PI
				var diff := fmod(target_angle - _orbit_angle + PI, TAU) - PI
				_orbit_angle += diff * delta * 0.5
			var ts_h := trackside_height + _pitch_offset * trackside_distance * trackside_pitch_scale
			_target_pos = Vector3(
				cos(_orbit_angle) * trackside_distance,
				max(0.5, ts_h),
				sin(_orbit_angle) * trackside_distance
			)
			_target_look = Vector3.ZERO
		Mode.GOALCAM:
			# Anchored behind the home goal by default; horizontal drag orbits
			# around the arena edge and vertical drag adjusts height.
			var base_angle := 0.0 * (TAU / 12.0) + (TAU / 24.0)
			var goal_angle := base_angle + _orbit_angle * goalcam_orbit_scale
			_target_pos = Vector3(
				cos(goal_angle) * (ArenaBuilder.WALL_RADIUS + goalcam_distance),
				goalcam_height + _pitch_offset * 5.0,
				sin(goal_angle) * (ArenaBuilder.WALL_RADIUS + goalcam_distance)
			)
			_target_look = Vector3.ZERO
		Mode.FOLLOW_BALL:
			# Slowly orbit around the ball so the view doesn't stay static.
			_orbit_angle += orbit_speed * delta
			var look_target := ball_world_pos
			var fb_h := follow_height + _pitch_offset * follow_distance * follow_pitch_scale
			_target_pos = look_target + Vector3(
				cos(_orbit_angle) * follow_distance,
				max(1.5, fb_h),
				sin(_orbit_angle) * follow_distance
			)
			_target_look = look_target
		Mode.FOLLOW_PLAYER:
			# Orbit around the ball carrier at a tighter radius.
			_orbit_angle += orbit_speed * delta
			var look_target := follow_target_pos
			if look_target == Vector3.ZERO:
				look_target = ball_world_pos
			var fp_h := follow_height * follow_player_height_scale + _pitch_offset * follow_close_distance * follow_pitch_scale
			_target_pos = look_target + Vector3(
				cos(_orbit_angle) * follow_close_distance,
				max(1.0, fp_h),
				sin(_orbit_angle) * follow_close_distance
			)
			_target_look = look_target


func _apply_overhead_instantly() -> void:
	_target_pos = Vector3(0, overhead_height, 0.1)
	_target_look = Vector3.ZERO
	if _camera:
		_camera.global_position = _target_pos
		_camera.look_at(_target_look, _look_up_vec())


func _apply_trackside_instantly() -> void:
	_target_pos = Vector3(
		cos(_orbit_angle) * trackside_distance,
		trackside_height,
		sin(_orbit_angle) * trackside_distance
	)
	_target_look = Vector3.ZERO
	if _camera:
		_camera.global_position = _target_pos
		_camera.look_at(_target_look, Vector3.UP)
