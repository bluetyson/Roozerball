## StadiumAtmosphere — Crowd stands, ambient particles, and arena decoration.
##
## Adds spectator stand geometry around the outer wall, ambient dust
## particles, and sector label markers on the track.
class_name StadiumAtmosphere
extends Node3D

const NUM_SECTORS := 12
const SECTOR_NAMES := ["A","B","C","D","E","F","G","H","I","J","K","L"]
const STAND_INNER_R := 17.5
const STAND_OUTER_R := 25.0
const STAND_BASE_Y := 1.2
const STAND_TOP_Y := 6.0
const STAND_COLOR := Color(0.12, 0.12, 0.16)
const CROWD_COLOR := Color(0.35, 0.30, 0.25)


func build() -> void:
	_build_stands()
	_build_sector_labels()
	_build_ambient_particles()


func _build_stands() -> void:
	# Tiered seating around the outer wall.
	var tiers := 4
	for tier_idx in range(tiers):
		var frac := float(tier_idx) / float(tiers)
		var r_in := STAND_INNER_R + frac * (STAND_OUTER_R - STAND_INNER_R)
		var r_out := r_in + (STAND_OUTER_R - STAND_INNER_R) / tiers
		var y := STAND_BASE_Y + frac * (STAND_TOP_Y - STAND_BASE_Y)
		var segments := 48
		for i in range(segments):
			var a0 := float(i) / segments * TAU
			var a1 := float(i + 1) / segments * TAU
			var st := SurfaceTool.new()
			st.begin(Mesh.PRIMITIVE_TRIANGLES)
			st.set_color(STAND_COLOR.lerp(CROWD_COLOR, frac * 0.5))
			st.set_normal(Vector3.UP)

			var p0 := Vector3(cos(a0) * r_in,  y, sin(a0) * r_in)
			var p1 := Vector3(cos(a1) * r_in,  y, sin(a1) * r_in)
			var p2 := Vector3(cos(a1) * r_out, y + 0.3, sin(a1) * r_out)
			var p3 := Vector3(cos(a0) * r_out, y + 0.3, sin(a0) * r_out)

			# Wound counter-clockwise when viewed from above (+Y).
			st.add_vertex(p0)
			st.add_vertex(p2)
			st.add_vertex(p1)
			st.add_vertex(p0)
			st.add_vertex(p3)
			st.add_vertex(p2)

			var mesh := st.commit()
			var inst := MeshInstance3D.new()
			inst.mesh = mesh
			var mat := StandardMaterial3D.new()
			mat.albedo_color = STAND_COLOR.lerp(CROWD_COLOR, frac * 0.5)
			mat.roughness = 0.9
			inst.material_override = mat
			add_child(inst)

	# Crowd silhouettes — small boxes scattered in the stands.
	var crowd_count := 200
	for _i in range(crowd_count):
		var angle := randf() * TAU
		var r := STAND_INNER_R + randf() * (STAND_OUTER_R - STAND_INNER_R)
		var tier_frac := (r - STAND_INNER_R) / (STAND_OUTER_R - STAND_INNER_R)
		var y := STAND_BASE_Y + tier_frac * (STAND_TOP_Y - STAND_BASE_Y) + 0.4

		var person := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = Vector3(0.2, 0.5, 0.15)
		person.mesh = box
		person.position = Vector3(cos(angle) * r, y, sin(angle) * r)

		var mat := StandardMaterial3D.new()
		# Random crowd colour.
		var hue := randf()
		mat.albedo_color = Color.from_hsv(hue, 0.3, 0.25 + randf() * 0.15)
		mat.roughness = 0.95
		person.material_override = mat
		add_child(person)


func _build_sector_labels() -> void:
	for i in range(NUM_SECTORS):
		var angle := i * (TAU / NUM_SECTORS) + (TAU / 24.0)
		var r := ArenaBuilder.WALL_RADIUS + 0.5
		var label := Label3D.new()
		label.text = SECTOR_NAMES[i]
		label.font_size = 72
		label.pixel_size = 0.01
		label.position = Vector3(cos(angle) * r, ArenaBuilder.RING_HEIGHTS["upper"] + 2.5, sin(angle) * r)
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.modulate = Color(0.8, 0.8, 0.9, 0.7)
		label.outline_size = 4
		add_child(label)


func _build_ambient_particles() -> void:
	# Godot GPUParticles3D for atmospheric dust motes.
	var particles := GPUParticles3D.new()
	particles.name = "AmbientDust"
	particles.amount = 150
	particles.lifetime = 8.0
	particles.visibility_aabb = AABB(Vector3(-20, -1, -20), Vector3(40, 15, 40))

	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	mat.emission_box_extents = Vector3(18, 6, 18)
	mat.direction = Vector3(0, 0.2, 0)
	mat.spread = 180.0
	mat.initial_velocity_min = 0.05
	mat.initial_velocity_max = 0.15
	mat.gravity = Vector3(0, -0.02, 0)
	mat.scale_min = 0.02
	mat.scale_max = 0.06
	mat.color = Color(1.0, 0.95, 0.85, 0.3)
	particles.process_material = mat

	# Simple quad mesh for each particle.
	var quad := QuadMesh.new()
	quad.size = Vector2(0.1, 0.1)
	particles.draw_pass_1 = quad

	add_child(particles)
