## CameraRig — Multi-mode camera system for the 3D arena.
##
## Supports three modes:
##   1  Overhead   — top-down view of the full arena
##   2  Trackside  — low-angle rotating view following the action
##   3  Goal-cam   — behind-the-goal view for scoring moments
##
## Press 1/2/3 to switch.  The rig smoothly interpolates between views.
class_name CameraRig
extends Node3D

enum Mode { OVERHEAD, TRACKSIDE, GOALCAM }

# ── configuration ────────────────────────────────────────────────────
@export var overhead_height := 32.0
@export var trackside_height := 4.0
@export var trackside_distance := 20.0
@export var goalcam_distance := 5.0
@export var goalcam_height := 3.0
@export var lerp_speed := 3.5
@export var orbit_speed := 0.15  # rad/s for trackside auto-orbit

# ── state ────────────────────────────────────────────────────────────
var current_mode: Mode = Mode.TRACKSIDE
var _orbit_angle := 0.0  # Current trackside orbit angle.
var _target_pos := Vector3.ZERO
var _target_look := Vector3.ZERO

var _camera: Camera3D = null

# Focus target (e.g., ball carrier sector).
var focus_sector: int = -1


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
	_camera.look_at(_target_look, _look_up_vec())


func _look_up_vec() -> Vector3:
	# Overhead mode looks nearly straight down, so Vector3.UP is almost
	# parallel to the view direction and causes a degenerate look_at.
	# Use -Z as the up reference instead, which is always stable.
	return Vector3(0.0, 0.0, -1.0) if current_mode == Mode.OVERHEAD else Vector3.UP


func _handle_input() -> void:
	if Input.is_action_just_pressed("camera_overhead"):
		current_mode = Mode.OVERHEAD
	elif Input.is_action_just_pressed("camera_trackside"):
		current_mode = Mode.TRACKSIDE
	elif Input.is_action_just_pressed("camera_goalcam"):
		current_mode = Mode.GOALCAM


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
			_target_pos = Vector3(
				cos(_orbit_angle) * trackside_distance,
				trackside_height,
				sin(_orbit_angle) * trackside_distance
			)
			_target_look = Vector3.ZERO
		Mode.GOALCAM:
			# Look from behind the home goal (sector 0) toward centre.
			var goal_angle := 0.0 * (TAU / 12.0) + (TAU / 24.0)
			_target_pos = Vector3(
				cos(goal_angle) * (ArenaBuilder.WALL_RADIUS + goalcam_distance),
				goalcam_height,
				sin(goal_angle) * (ArenaBuilder.WALL_RADIUS + goalcam_distance)
			)
			_target_look = Vector3.ZERO


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
