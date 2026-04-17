## ArenaBuilder — Procedurally generates the 3D circular banked track.
##
## Creates 12 sectors × 4 playable rings (floor, lower, middle, upper)
## as tilted mesh surfaces arranged in a circular arena.  Each square
## is represented by a StaticBody3D with a visual MeshInstance3D child
## so figures can be placed on them.
##
## The arena is centred at the world origin; the track winds
## counter-clockwise (positive-Y up, XZ plane for the circle).
class_name ArenaBuilder
extends Node3D

# ── constants ────────────────────────────────────────────────────────
const NUM_SECTORS := 12
const SECTOR_NAMES := ["A","B","C","D","E","F","G","H","I","J","K","L"]

## Ring radii (inner, outer) in world units.
const RING_RADII := {
	"floor":  [3.0,  5.5],
	"lower":  [5.5,  8.5],
	"middle": [8.5, 12.0],
	"upper":  [12.0, 16.0],
}

## Ring incline angles (degrees) — the track is banked inward.
const RING_INCLINE := {
	"floor":  0.0,
	"lower":  12.0,
	"middle": 22.0,
	"upper":  32.0,
}

## Squares per ring per sector (matches engine constants).
const SQUARES_PER_RING := {
	"floor":  1,
	"lower":  2,
	"middle": 3,
	"upper":  4,
}

## Number of angular sub-steps used when building each sector arc quad.
## Higher values produce rounder-looking rings (48 steps total for a full
## circle when NUM_SECTORS == 12 and ARC_SUBDIVISIONS == 4).
const ARC_SUBDIVISIONS := 4

const RING_HEIGHTS := {
	"floor":  0.0,
	"lower":  0.3,
	"middle": 0.7,
	"upper":  1.2,
}

## Team colours.
const HOME_COLOR := Color(0.12, 0.47, 0.71)   # blue
const VISITOR_COLOR := Color(0.84, 0.15, 0.16) # red
const GOAL_COLOR := Color(1.0, 0.85, 0.0, 0.8) # gold

## Track surface colours per ring.
const RING_COLORS := {
	"floor":  Color(0.18, 0.18, 0.22),
	"lower":  Color(0.22, 0.22, 0.28),
	"middle": Color(0.26, 0.26, 0.32),
	"upper":  Color(0.30, 0.30, 0.36),
}

# Outer wall.
const WALL_RADIUS := 17.0
const WALL_HEIGHT := 2.0

# ── public members ───────────────────────────────────────────────────
## Dictionary keyed by "sector_ring_position" → Node3D anchor.
var square_anchors: Dictionary = {}

## Goal markers (sector 0 = home goal, sector 6 = visitor goal).
var goal_markers: Dictionary = {}


# ── build ────────────────────────────────────────────────────────────

func build() -> void:
	_build_track_surface()
	_build_outer_wall()
	_build_goals()
	_build_cannon_turret()
	_build_floor_surface()


func _build_track_surface() -> void:
	for sector_idx in range(NUM_SECTORS):
		var angle_start := sector_idx * (TAU / NUM_SECTORS)
		var angle_end := (sector_idx + 1) * (TAU / NUM_SECTORS)

		for ring_name in ["floor", "lower", "middle", "upper"]:
			var inner_r: float = RING_RADII[ring_name][0]
			var outer_r: float = RING_RADII[ring_name][1]
			var height: float = RING_HEIGHTS[ring_name]
			var incline_deg: float = RING_INCLINE[ring_name]
			var sq_count: int = SQUARES_PER_RING[ring_name]
			var base_color: Color = RING_COLORS[ring_name]

			for sq_pos in range(sq_count):
				# Subdivide the ring within this sector.
				var frac_start := float(sq_pos) / float(sq_count)
				var frac_end := float(sq_pos + 1) / float(sq_count)
				# Interpolate radii for sub-positions.
				var r_in := inner_r
				var r_out := outer_r

				# Angular sub-span.
				var a0 := angle_start + frac_start * (angle_end - angle_start)
				var a1 := angle_start + frac_end * (angle_end - angle_start)

				# Build the quad mesh for this square.
				var mesh_inst := _create_track_quad(a0, a1, r_in, r_out, height, incline_deg, base_color, sector_idx, ring_name, sq_pos)
				add_child(mesh_inst)

				# Store anchor at the centre of the quad.
				var mid_angle := (a0 + a1) * 0.5
				var mid_r := (r_in + r_out) * 0.5
				var anchor := Node3D.new()
				anchor.position = Vector3(
					cos(mid_angle) * mid_r,
					height,
					sin(mid_angle) * mid_r
				)
				anchor.name = "Anchor_%s_%s_%d" % [SECTOR_NAMES[sector_idx], ring_name, sq_pos]
				add_child(anchor)

				var key := "%d_%s_%d" % [sector_idx, ring_name, sq_pos]
				square_anchors[key] = anchor


func _create_track_quad(a0: float, a1: float, r_in: float, r_out: float,
						height: float, _incline_deg: float, color: Color,
						_sector_idx: int, _ring_name: String, _sq_pos: int) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	st.set_color(color)
	st.set_normal(Vector3.UP)

	# Subdivide the arc into ARC_SUBDIVISIONS steps so the ring edges follow
	# the actual curve instead of a single straight chord.  This prevents the
	# rings from looking like flat-edged polygons ("cut-off circles") in the
	# overhead view.
	for step in range(ARC_SUBDIVISIONS):
		var t0 := float(step)       / float(ARC_SUBDIVISIONS)
		var t1 := float(step + 1)   / float(ARC_SUBDIVISIONS)
		var sa := a0 + t0 * (a1 - a0)
		var ea := a0 + t1 * (a1 - a0)

		var p0 := Vector3(cos(sa) * r_in,  height, sin(sa) * r_in)
		var p1 := Vector3(cos(ea) * r_in,  height, sin(ea) * r_in)
		var p2 := Vector3(cos(ea) * r_out, height, sin(ea) * r_out)
		var p3 := Vector3(cos(sa) * r_out, height, sin(sa) * r_out)

		# Triangle 1 — wound counter-clockwise when viewed from above (+Y).
		st.add_vertex(p0)
		st.add_vertex(p2)
		st.add_vertex(p1)
		# Triangle 2.
		st.add_vertex(p0)
		st.add_vertex(p3)
		st.add_vertex(p2)

	var mesh := st.commit()
	var inst := MeshInstance3D.new()
	inst.mesh = mesh

	# Material.
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.85
	mat.metallic = 0.05
	inst.material_override = mat

	return inst


func _build_outer_wall() -> void:
	var segments := 64
	for i in range(segments):
		var a0 := float(i) / segments * TAU
		var a1 := float(i + 1) / segments * TAU
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)

		var base_y: float = RING_HEIGHTS["upper"]
		var p0 := Vector3(cos(a0) * WALL_RADIUS, base_y, sin(a0) * WALL_RADIUS)
		var p1 := Vector3(cos(a1) * WALL_RADIUS, base_y, sin(a1) * WALL_RADIUS)
		var p2 := Vector3(cos(a1) * WALL_RADIUS, base_y + WALL_HEIGHT, sin(a1) * WALL_RADIUS)
		var p3 := Vector3(cos(a0) * WALL_RADIUS, base_y + WALL_HEIGHT, sin(a0) * WALL_RADIUS)

		var normal := Vector3(cos((a0 + a1) * 0.5), 0.0, sin((a0 + a1) * 0.5)).normalized() * -1.0
		st.set_normal(normal)
		st.set_color(Color(0.35, 0.35, 0.4))

		st.add_vertex(p0)
		st.add_vertex(p1)
		st.add_vertex(p2)
		st.add_vertex(p0)
		st.add_vertex(p2)
		st.add_vertex(p3)

		var mesh := st.commit()
		var inst := MeshInstance3D.new()
		inst.mesh = mesh
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.35, 0.35, 0.4)
		mat.roughness = 0.6
		mat.metallic = 0.2
		inst.material_override = mat
		add_child(inst)


func _build_goals() -> void:
	# Home goal at sector 0, visitor goal at sector 6.
	for goal_sector: int in [0, 6]:
		var a_start := goal_sector * (TAU / NUM_SECTORS)
		var a_end := (goal_sector + 1) * (TAU / NUM_SECTORS)
		var mid_a := (a_start + a_end) * 0.5

		# Goal opening in the outer wall.
		var goal_node := Node3D.new()
		goal_node.name = "Goal_%s" % ("Home" if goal_sector == 0 else "Visitor")

		# Goal frame (two posts + crossbar).
		var post_height := 1.8
		var post_radius := 0.08
		var goal_width := 1.5  # Half-angle span at the wall.
		var base_y: float = RING_HEIGHTS["upper"]
		var goal_color: Color = HOME_COLOR if goal_sector == 0 else VISITOR_COLOR

		for offset: float in [-1.0, 1.0]:
			var post_angle := mid_a + offset * (goal_width / WALL_RADIUS)
			var post := _create_cylinder(post_radius, post_height, goal_color)
			post.position = Vector3(
				cos(post_angle) * WALL_RADIUS,
				base_y + post_height * 0.5,
				sin(post_angle) * WALL_RADIUS
			)
			goal_node.add_child(post)

		# Crossbar.
		var crossbar := _create_cylinder(post_radius * 0.8, goal_width * 2.0, goal_color)
		crossbar.position = Vector3(
			cos(mid_a) * WALL_RADIUS,
			base_y + post_height,
			sin(mid_a) * WALL_RADIUS
		)
		crossbar.rotation_degrees.z = 90.0
		goal_node.add_child(crossbar)

		# Glowing goal zone marker.
		var glow := _create_goal_glow(mid_a, base_y, goal_color)
		goal_node.add_child(glow)

		add_child(goal_node)
		goal_markers[goal_sector] = goal_node


func _build_cannon_turret() -> void:
	var turret := Node3D.new()
	turret.name = "CannonTurret"

	# Central pedestal.
	var pedestal := _create_cylinder(0.6, 2.5, Color(0.25, 0.25, 0.3))
	pedestal.position = Vector3(0, 1.25, 0)
	turret.add_child(pedestal)

	# Barrel.
	var barrel := _create_cylinder(0.15, 2.0, Color(0.4, 0.35, 0.3))
	barrel.position = Vector3(0, 2.5, -0.8)
	barrel.rotation_degrees.x = -30.0
	turret.add_child(barrel)

	add_child(turret)


func _build_floor_surface() -> void:
	# Central arena floor (inside the track).
	var disc := _create_disc(3.0, Color(0.1, 0.1, 0.12))
	add_child(disc)


# ── geometry helpers ─────────────────────────────────────────────────

func _create_cylinder(radius: float, height: float, color: Color) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 16
	var inst := MeshInstance3D.new()
	inst.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.5
	mat.metallic = 0.3
	inst.material_override = mat
	return inst


func _create_goal_glow(angle: float, base_y: float, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = Vector3(2.0, 0.05, 2.0)
	var inst := MeshInstance3D.new()
	inst.mesh = mesh
	inst.position = Vector3(
		cos(angle) * (WALL_RADIUS - 1.0),
		base_y + 0.02,
		sin(angle) * (WALL_RADIUS - 1.0)
	)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(color.r, color.g, color.b, 0.4)
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 2.0
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	inst.material_override = mat
	return inst


func _create_disc(radius: float, color: Color) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.set_color(color)
	st.set_normal(Vector3.UP)
	var segments := 48
	for i in range(segments):
		var a0 := float(i) / segments * TAU
		var a1 := float(i + 1) / segments * TAU
		st.add_vertex(Vector3.ZERO)
		st.add_vertex(Vector3(cos(a0) * radius, 0, sin(a0) * radius))
		st.add_vertex(Vector3(cos(a1) * radius, 0, sin(a1) * radius))
	var mesh := st.commit()
	var inst := MeshInstance3D.new()
	inst.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	inst.material_override = mat
	return inst


# ── utility ──────────────────────────────────────────────────────────

## Convert engine coordinates (sector_index, ring_name, position) to
## a world-space Vector3 suitable for placing a figure.
func get_square_world_pos(sector_idx: int, ring_name: String, position: int) -> Vector3:
	var key := "%d_%s_%d" % [sector_idx, ring_name, position]
	if square_anchors.has(key):
		return (square_anchors[key] as Node3D).global_position
	# Fallback: compute from geometry.
	var r_in: float = RING_RADII.get(ring_name, [8.0, 12.0])[0]
	var r_out: float = RING_RADII.get(ring_name, [8.0, 12.0])[1]
	var sq_count: int = SQUARES_PER_RING.get(ring_name, 1)
	var angle_start := sector_idx * (TAU / NUM_SECTORS)
	var angle_end := (sector_idx + 1) * (TAU / NUM_SECTORS)
	var frac_mid := (float(position) + 0.5) / float(sq_count)
	var mid_angle := angle_start + frac_mid * (angle_end - angle_start)
	var mid_r := (r_in + r_out) * 0.5
	var height: float = RING_HEIGHTS.get(ring_name, 0.0)
	return Vector3(cos(mid_angle) * mid_r, height, sin(mid_angle) * mid_r)
