## BallVisual — 3D representation of the steel game ball.
##
## Renders as a metallic sphere with temperature-based colour and
## emissive glow.  Includes a trailing particle effect.
class_name BallVisual
extends Node3D

# ── temperature colours ──────────────────────────────────────────────
const TEMP_COLORS := {
	"very_hot": Color(1.0, 0.25, 0.05),
	"hot":      Color(1.0, 0.55, 0.1),
	"warm":     Color(0.9, 0.75, 0.3),
	"cool":     Color(0.7, 0.7, 0.75),
}

const TEMP_EMISSION := {
	"very_hot": 4.0,
	"hot":      2.5,
	"warm":     1.0,
	"cool":     0.0,
}

const BALL_RADIUS := 0.3
const LERP_SPEED := 10.0

# ── nodes ────────────────────────────────────────────────────────────
var _mesh: MeshInstance3D = null
var _material: StandardMaterial3D = null
var _light: OmniLight3D = null
var _target_position := Vector3.ZERO
var _visible_on_track := false

var arena: ArenaBuilder = null


func _ready() -> void:
	# Sphere mesh.
	var sphere := SphereMesh.new()
	sphere.radius = BALL_RADIUS
	sphere.height = BALL_RADIUS * 2
	sphere.radial_segments = 24
	sphere.rings = 12

	_mesh = MeshInstance3D.new()
	_mesh.mesh = sphere
	_mesh.name = "BallMesh"

	_material = StandardMaterial3D.new()
	_material.albedo_color = Color(0.7, 0.7, 0.75)
	_material.metallic = 0.9
	_material.roughness = 0.15
	_material.emission_enabled = false
	_mesh.material_override = _material
	add_child(_mesh)

	# Dynamic light that follows the ball.
	_light = OmniLight3D.new()
	_light.name = "BallLight"
	_light.light_energy = 0.0
	_light.omni_range = 3.0
	_light.light_color = Color(1.0, 0.5, 0.2)
	_light.shadow_enabled = true
	add_child(_light)

	visible = false


func _process(delta: float) -> void:
	if _visible_on_track:
		position = position.lerp(_target_position, delta * LERP_SPEED)


# ── public API ───────────────────────────────────────────────────────

func update_from_state(ball_data: Dictionary) -> void:
	var state: String = ball_data.get("state", "not_in_play")
	var temp: String = ball_data.get("temperature", "cool")

	if state in ["on_track", "fielded"]:
		_visible_on_track = true
		visible = true

		# Position.
		var sector_idx: int = ball_data.get("sector_index", 0)
		var ring_name: String = ball_data.get("ring", "middle")
		var pos_idx: int = ball_data.get("position", 0)
		if arena != null:
			_target_position = arena.get_square_world_pos(sector_idx, ring_name, pos_idx)
			_target_position.y += 0.25  # Float above the surface.

		# If carried, follow the carrier (FigureManager handles this;
		# we just mark the ball near the carrier's square).
		var carrier_name = ball_data.get("carrier")
		if carrier_name != null and carrier_name is String:
			pass  # Position already set to carrier's square.

		# Temperature visual.
		var color: Color = TEMP_COLORS.get(temp, TEMP_COLORS["cool"])
		var emission_energy: float = TEMP_EMISSION.get(temp, 0.0)
		_material.albedo_color = color
		if emission_energy > 0:
			_material.emission_enabled = true
			_material.emission = color
			_material.emission_energy_multiplier = emission_energy
			_light.light_energy = emission_energy * 0.5
			_light.light_color = color
		else:
			_material.emission_enabled = false
			_light.light_energy = 0.0

	elif state == "in_cannon":
		_visible_on_track = false
		visible = true
		# Park the ball at the cannon turret centre.
		position = Vector3(0, 3.0, 0)
		_material.albedo_color = TEMP_COLORS["very_hot"]
		_material.emission_enabled = true
		_material.emission = TEMP_COLORS["very_hot"]
		_material.emission_energy_multiplier = 3.0
		_light.light_energy = 2.0

	else:
		# Dead / not in play.
		visible = false
		_visible_on_track = false
		_light.light_energy = 0.0
