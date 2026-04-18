## FigureManager — Creates, updates and animates 3D figure representations.
##
## Each figure from the Python engine is represented by a small 3D mesh
## (capsule for skaters/catchers, box for bikers) parented to the arena.
## On each state update the manager lerps figures to their new positions.
class_name FigureManager
extends Node3D

# ── constants ────────────────────────────────────────────────────────
const FIGURE_SCALE := Vector3(0.25, 0.25, 0.25)
const BIKER_SCALE := Vector3(0.7, 0.4, 1.0)
const LERP_SPEED := 8.0

# Team colours.
const TEAM_COLORS := {
	"home": Color(0.12, 0.47, 0.71),
	"visitor": Color(0.84, 0.15, 0.16),
}

# Type-specific accent colours (multiplied with team colour).
const TYPE_ACCENTS := {
	"bruiser": Color(0.8, 0.8, 1.0),
	"speeder": Color(0.5, 1.0, 1.0),
	"catcher": Color(0.5, 1.0, 0.6),
	"biker":   Color(0.7, 0.5, 1.0),
}

# Figure type labels shown as billboards.
const TYPE_LABELS := {
	"bruiser": "B",
	"speeder": "S",
	"catcher": "C",
	"biker":   "K",
}

# ── state ────────────────────────────────────────────────────────────
## Dictionary keyed by figure name → Node3D instance.
var _figures: Dictionary = {}

## Target positions for smooth lerp.  Keyed by figure name.
var _target_positions: Dictionary = {}

## Reference to the ArenaBuilder for coordinate conversion.
var arena: ArenaBuilder = null


func _process(delta: float) -> void:
	# Smoothly move figures toward their target positions.
	for fig_name in _target_positions:
		if _figures.has(fig_name):
			var node: Node3D = _figures[fig_name]
			var target: Vector3 = _target_positions[fig_name]
			node.position = node.position.lerp(target, delta * LERP_SPEED)


# ── public API ───────────────────────────────────────────────────────

## Rebuild all figures from a full board state dictionary.
func update_from_state(board_data: Array, home_team: Dictionary, visitor_team: Dictionary) -> void:
	# Collect all figures mentioned in the state and their positions.
	var figure_states: Dictionary = {}  # name → {type, team, status, pos, has_ball, ...}

	for sq in board_data:
		var sector_idx: int = sq.get("sector", 0)
		var ring_name: String = sq.get("ring", "middle")
		var position: int = sq.get("position", 0)
		var figures: Array = sq.get("figures", [])
		for i in range(figures.size()):
			var fig: Dictionary = figures[i]
			var fig_name: String = fig.get("name", "Unknown")
			figure_states[fig_name] = {
				"type": fig.get("type", "bruiser"),
				"team": fig.get("team", "home"),
				"status": fig.get("status", "standing"),
				"has_ball": fig.get("has_ball", false),
				"sector_index": sector_idx,
				"ring": ring_name,
				"position": position,
				"slot_offset": i,
			}

	# Create new figure nodes / update existing.
	for fig_name in figure_states:
		var info: Dictionary = figure_states[fig_name]
		var is_new := not _figures.has(fig_name)
		if is_new:
			_create_figure_node(fig_name, info)
		_update_figure_visual(fig_name, info)

		# Compute world position.
		if arena != null:
			var base_pos := arena.get_square_world_pos(
				info["sector_index"], info["ring"], info["position"]
			)
			# Offset within the square so multiple figures don't overlap.
			var slot_off: int = info["slot_offset"]
			var offset := Vector3(
				sin(slot_off * 1.2) * 0.3,
				0.15,  # Slight hover above surface.
				cos(slot_off * 1.2) * 0.3,
			)
			_target_positions[fig_name] = base_pos + offset
			# Snap newly-created figures to their position immediately so
			# they don't visibly lerp from the scene origin on first spawn.
			if is_new:
				_figures[fig_name].position = base_pos + offset

	# Remove figures no longer on the board.
	var to_remove: Array[String] = []
	for fig_name in _figures:
		if not figure_states.has(fig_name):
			to_remove.append(fig_name)
	for fig_name in to_remove:
		(_figures[fig_name] as Node3D).queue_free()
		_figures.erase(fig_name)
		_target_positions.erase(fig_name)


## Return the current world-space position of a named figure, or Vector3.ZERO
## if the figure does not exist.
func get_figure_world_pos(fig_name: String) -> Vector3:
	var node: Node3D = _figures.get(fig_name)
	if node == null:
		return Vector3.ZERO
	return node.global_position


## Highlight a specific figure (e.g. ball carrier).
func highlight_figure(fig_name: String, color: Color) -> void:
	if _figures.has(fig_name):
		var node: Node3D = _figures[fig_name]
		var mesh_inst := node.get_node_or_null("Mesh") as MeshInstance3D
		if mesh_inst and mesh_inst.material_override:
			(mesh_inst.material_override as StandardMaterial3D).emission = color
			(mesh_inst.material_override as StandardMaterial3D).emission_enabled = true
			(mesh_inst.material_override as StandardMaterial3D).emission_energy_multiplier = 1.5


## Clear emission highlight from a figure.
func clear_highlight(fig_name: String) -> void:
	if _figures.has(fig_name):
		var node: Node3D = _figures[fig_name]
		var mesh_inst := node.get_node_or_null("Mesh") as MeshInstance3D
		if mesh_inst and mesh_inst.material_override:
			(mesh_inst.material_override as StandardMaterial3D).emission_enabled = false


# ── internal ─────────────────────────────────────────────────────────

func _create_figure_node(fig_name: String, info: Dictionary) -> void:
	var root := Node3D.new()
	root.name = fig_name.replace(" ", "_")

	var mesh_inst := MeshInstance3D.new()
	mesh_inst.name = "Mesh"

	var fig_type: String = info.get("type", "bruiser")
	if fig_type == "biker":
		var box := BoxMesh.new()
		box.size = BIKER_SCALE
		mesh_inst.mesh = box
	else:
		var capsule := CapsuleMesh.new()
		capsule.radius = 0.35
		capsule.height = 0.85
		mesh_inst.mesh = capsule

	# Material.
	var mat := StandardMaterial3D.new()
	var team_col: Color = TEAM_COLORS.get(info.get("team", "home"), TEAM_COLORS["home"])
	var accent: Color = TYPE_ACCENTS.get(fig_type, Color.WHITE)
	mat.albedo_color = team_col * accent
	mat.roughness = 0.4   # Lower roughness makes figures shinier, improving visibility under spotlights.
	mat.metallic = 0.3    # Slightly metallic so floodlights produce specular highlights.
	mesh_inst.material_override = mat

	root.add_child(mesh_inst)

	# Label billboard.
	var label := Label3D.new()
	label.name = "Label"
	label.text = TYPE_LABELS.get(fig_type, "?")
	label.font_size = 48
	label.pixel_size = 0.015
	label.position = Vector3(0, 0.7, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color.WHITE
	label.outline_size = 8
	root.add_child(label)

	add_child(root)
	_figures[fig_name] = root


func _update_figure_visual(fig_name: String, info: Dictionary) -> void:
	var node: Node3D = _figures.get(fig_name)
	if node == null:
		return

	var mesh_inst := node.get_node_or_null("Mesh") as MeshInstance3D
	if mesh_inst == null:
		return

	var mat := mesh_inst.material_override as StandardMaterial3D
	if mat == null:
		return

	# Update colour based on status.
	var status: String = info.get("status", "standing")
	var team_col: Color = TEAM_COLORS.get(info.get("team", "home"), TEAM_COLORS["home"])
	var accent: Color = TYPE_ACCENTS.get(info.get("type", "bruiser"), Color.WHITE)
	var base_col := team_col * accent

	match status:
		"fallen":
			base_col = base_col.darkened(0.4)
			node.rotation_degrees.z = 60.0
		"shaken", "badly_shaken":
			base_col = base_col.darkened(0.25)
			node.rotation_degrees.z = 0.0
		"injured":
			base_col = base_col.darkened(0.5)
			node.rotation_degrees.z = 30.0
		"unconscious", "dead":
			base_col = Color(0.3, 0.3, 0.3)
			node.rotation_degrees.z = 90.0
		_:
			node.rotation_degrees.z = 0.0

	mat.albedo_color = base_col

	# Ball carrier glow.
	if info.get("has_ball", false):
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.9, 0.2)
		mat.emission_energy_multiplier = 2.0
	else:
		mat.emission_enabled = false

	# Update label.
	var label := node.get_node_or_null("Label") as Label3D
	if label:
		var lbl_text: String = TYPE_LABELS.get(info.get("type", "bruiser"), "?")
		if info.get("has_ball", false):
			lbl_text += " ●"
		label.text = lbl_text
