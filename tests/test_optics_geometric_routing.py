"""W2 public validation, finite geometry, ownership and actual resource limits."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import itertools
import math

import numpy as np
import pytest

import ohlab.optics.geometric_routing as routing
from ohlab.optics.geometric_routing import (
    GeometricScene, NumericalAmbiguityError, trace_routes, validate_scene,
)


def element(identity, kind, position, y=0., *, angles=None, aperture=None):
    return {"id": identity, "kind": kind, "pose": {"position_m": list(position),
            "rotation_xyz_rad": list(angles if angles is not None else (0., y, 0.))},
            "aperture": aperture or {"kind": "disk", "radius_m": .025}}


def scene(elements=(), *, origin=(0., .08, 0.), direction=(0., 0., 1.)):
    return {"schema_version": 1, "model_contract": "w2_ideal_geometric_routing_v1",
            "source": {"id": "source", "origin_m": list(origin), "direction": list(direction), "relative_weight": 1.},
            "elements": list(elements)}


def folded(two=False):
    first = element("M1", "mirror", (0., .08, .2), -math.pi/4)
    if not two:
        return scene([first, element("D", "receiver", (.2, .08, .2), -math.pi/2)])
    return scene([first, element("M2", "mirror", (.2, .08, .2), 3*math.pi/4),
                  element("D", "receiver", (.2, .08, .4), math.pi)])


def split_scene(blocked=False):
    elements = [element("S", "ideal_splitter_50_50", (0., .08, .2), -math.pi/4),
                element("DT", "receiver", (0., .08, .4), math.pi),
                element("DR", "receiver", (.2, .08, .2), -math.pi/2)]
    if blocked:
        elements.append(element("stop", "beam_stop", (.1, .08, .2), -math.pi/2))
    return scene(elements)


def run(value):
    return trace_routes(GeometricScene.from_dict(value))


def assert_ledger(result):
    assert result.ledger["signed_residual"] == 0.  # dyadic halves and exact source1
    assert math.fsum(t["relative_weight"] for t in result.terminals) == 1.
    assert len({t["branch_id"] for t in result.terminals}) == len(result.terminals)
    assert len(result.segments)+len(result.hits) <= 256
    assert len(result.branches) <= 63 and len(result.hits) <= 128
    assert result.status == ("incomplete" if result.ledger["truncated_weight"] else "complete")


@pytest.mark.parametrize("two,expected_ids,expected_length", [(False, ["M1", "D"], .4), (True, ["M1", "M2", "D"], .6)])
def test_actual_frozen_folds(two, expected_ids, expected_length):
    result = run(folded(two))
    assert [h["element_id"] for h in result.hits] == expected_ids
    assert result.terminals[0]["category"] == "detected"
    assert result.terminals[0]["cumulative_length_m"] == pytest.approx(expected_length, rel=2e-13, abs=2e-13)
    assert result.ledger["detected_weight"] == 1.
    assert_ledger(result)


def test_split_children_and_stop_are_actual_intersections_with_separate_weights():
    open_result, blocked = run(split_scene()), run(split_scene(True))
    assert [b["id"] for b in open_result.branches] == ["r0", "r0.T", "r0.R"]
    assert open_result.branches[0]["outcome"] == "split"
    assert [(x["branch_id"], x["category"], x["relative_weight"]) for x in open_result.terminals] == [
        ("r0.T", "detected", .5), ("r0.R", "detected", .5)]
    assert blocked.ledger["detected_weight"] == blocked.ledger["absorbed_weight"] == .5
    assert blocked.hits[-1]["element_id"] == "stop"
    assert blocked.terminals[-1]["cumulative_length_m"] == pytest.approx(.3, rel=2e-13, abs=2e-13)
    assert open_result.hits[1] == blocked.hits[1]
    assert_ledger(open_result)
    assert_ledger(blocked)


def test_pose_edit_really_misses_and_escape_endpoint_is_not_receiver():
    draft = folded(True)
    draft["elements"][1]["pose"]["rotation_xyz_rad"][1] += math.radians(10.)
    result = run(draft)
    assert [h["element_id"] for h in result.hits] == ["M1", "M2"]
    terminal = result.terminals[0]
    assert terminal["category"] == "escaped" and terminal["element_id"] is terminal["hit_id"] is None
    assert math.dist(terminal["position_m"], draft["source"]["origin_m"]) == pytest.approx(1., rel=2e-13, abs=2e-13)
    assert terminal["position_m"] != tuple(draft["elements"][-1]["pose"]["position_m"])


@pytest.mark.parametrize("aperture", [{"kind": "disk", "radius_m": .025}, {"kind": "rectangle", "width_m": .05, "height_m": .03}])
def test_finite_off_axis_hit_miss_and_local_coordinates(aperture):
    receiver = element("D", "receiver", (0., .08, .2), aperture=aperture)
    hit = run(scene([receiver], origin=(.01, .085, 0.)))
    np.testing.assert_allclose(hit.hits[0]["local_uv_m"], [.01, .005], rtol=2e-13, atol=2e-13)
    miss = run(scene([receiver], origin=(.06, .08, 0.)))
    assert not miss.hits and miss.ledger["escaped_weight"] == 1.


@pytest.mark.parametrize("sign", [-1., 1.])
def test_edge_approaches_are_classified_without_aperture_inflation(sign):
    receiver = element("D", "receiver", (0., .08, .2))
    inside = run(scene([receiver], origin=(sign*(.025-1e-8), .08, 0.)))
    outside = run(scene([receiver], origin=(sign*(.025+1e-8), .08, 0.)))
    assert inside.ledger["detected_weight"] == 1. and outside.ledger["escaped_weight"] == 1.
    with pytest.raises(NumericalAmbiguityError, match="edge"):
        run(scene([receiver], origin=(sign*.025, .08, 0.)))


@pytest.mark.parametrize("x",[math.nextafter(.025,0.),math.nextafter(.025,math.inf)])
def test_unresolved_adjacent_float_edge_is_not_forced_inside_or_outside(x):
    with pytest.raises(NumericalAmbiguityError,match="edge"):
        run(scene([element("D","receiver",(0.,.08,.2))],origin=(x,.08,0.)))


def test_admitted_nominal_unit_direction_is_not_silently_normalized():
    supplied=(0.,0.,1.+16*np.finfo(float).eps)
    result=run(scene(direction=supplied))
    assert result.scene.source["direction"]==supplied
    assert result.segments[0]["direction"]==supplied
    assert result.segments[0]["length_m"]==pytest.approx(1.,rel=0.,abs=2e-13)


def test_nearest_is_catalog_independent_and_close_tie_does_not_choose_array_order():
    near = element("near", "receiver", (0., .08, .2))
    far = element("far", "beam_stop", (0., .08, .4))
    outcomes = [run(scene(order)).to_dict() for order in itertools.permutations([near, far])]
    for outcome in outcomes:
        assert outcome["hits"][0]["element_id"] == "near"
        assert outcome["ledger"]["detected_weight"] == 1.
    almost = element("close", "receiver", (0., .08, .2+1e-16))
    for order in itertools.permutations([near, almost]):
        with pytest.raises(NumericalAmbiguityError, match="order/tie"):
            run(scene(order))


def test_irrelevant_coplanar_plane_is_culled_before_it_can_poison_hit():
    # Source lies in this remote disk's plane; the finite disk is .2m off ray.
    remote = element("remote", "mirror", (.2, .08, .2), 0.)
    receiver = element("D", "receiver", (0., .08, .4))
    result = run(scene([remote, receiver], direction=(0., 0., 1.)))
    assert [h["element_id"] for h in result.hits] == ["D"]
    # Exactly coplanar +X ray and finite Z-normal face centered on the ray.
    far_grazing = element("far_grazing", "mirror", (.5, .08, 0.))
    close_receiver = element("near", "receiver", (.1, .08, 0.), math.pi/2)
    result = run(scene([far_grazing, close_receiver], direction=(1., 0., 0.)))
    assert result.hits[0]["element_id"] == "near"
    with pytest.raises(NumericalAmbiguityError, match="parallel/coplanar/grazing"):
        run(scene([far_grazing], direction=(1., 0., 0.)))


def test_two_mirror_design_source_on_remote_infinite_extension_is_valid():
    # Frozen B source is on M2's infinite extension, not its finite aperture.
    result = run(folded(True))
    assert len(result.hits) == 3 and result.status == "complete"


def test_no_fixed_origin_offset_skips_a_distinct_nearby_face():
    draft = scene([element("S", "ideal_splitter_50_50", (0., .08, .2)),
                   element("near", "receiver", (0., .08, .2+1e-12))])
    result = run(draft)
    assert any(h["element_id"] == "near" for h in result.hits)
    assert result.ledger["detected_weight"] == .5
    assert result.hits[1]["segment_length_m"] > 0.


def test_32_legal_revisits_are_not_permanently_blacklisted():
    result = run(scene([element("plus", "mirror", (0., .08, .1)), element("minus", "mirror", (0., .08, -.1))]))
    assert [h["element_id"] for h in result.hits[:6]] == ["plus", "minus"]*3
    assert len(result.hits) == 32
    assert result.terminals[0]["reason"] == "interaction_cap"
    assert result.terminals[0]["cumulative_length_m"] == pytest.approx(6.3, rel=2e-13, abs=2e-13)
    assert len(result.branches) == 1
    assert_ledger(result)


def test_accumulated_distance_terminates_at_real_cap_point_without_fake_hit():
    result = run(scene([element("plus", "mirror", (0., .08, .8)), element("minus", "mirror", (0., .08, -.8))]))
    assert result.terminals[0]["reason"] == "distance_cap"
    assert result.terminals[0]["cumulative_length_m"] == pytest.approx(10., rel=0., abs=2e-13)
    assert result.segments[-1]["hit_id"] is None
    assert len(result.hits) == 6
    assert_ledger(result)


@pytest.mark.parametrize("kind,outcome", [("receiver","detected"),("beam_stop","absorbed"),("ideal_splitter_50_50","resource_truncated")])
def test_32nd_physical_event_is_processed_before_continuation_limit(kind,outcome):
    dz=math.sqrt(1-.01**2)
    final_x=.01*(.1+31*.2)/dz
    upper=element("plus","mirror",(.03,.08,.1),aperture={"kind":"rectangle","width_m":.2,"height_m":.05})
    lower=element("minus","mirror",(.03,.08,-.1),aperture={"kind":"rectangle","width_m":.061,"height_m":.05})
    last=element("last",kind,(final_x,.08,-.1),aperture={"kind":"disk","radius_m":.0015})
    result=run(scene([upper,lower,last],direction=(.01,0.,dz)))
    assert len(result.hits)==32 and result.hits[-1]["element_id"]=="last"
    assert all(t["category"]==outcome for t in result.terminals)
    if kind=="ideal_splitter_50_50":
        assert len(result.branches)==3
        assert [b["start_interaction_count"] for b in result.branches[1:]]==[32,32]
        assert all(t["reason"]=="interaction_cap" and t["hit_id"]==result.hits[-1]["id"] for t in result.terminals)
        assert all(not any(s["branch_id"]==b["id"] for s in result.segments) for b in result.branches[1:])
    else:assert result.status=="complete"
    assert_ledger(result)


def test_unresolved_hit_distance_cap_equality_is_not_nominally_tiebroken():
    with pytest.raises(NumericalAmbiguityError,match="boundary ordering"):
        run(scene([element("plus","mirror",(0.,.08,.4)),element("minus","mirror",(0.,.08,-.4))]))


def test_closed_rectangle_edge_and_exact_launch_are_explicitly_ambiguous():
    receiver=element("D","receiver",(0.,.08,.2),aperture={"kind":"rectangle","width_m":.05,"height_m":.03})
    with pytest.raises(NumericalAmbiguityError,match="rectangle edge"):
        run(scene([receiver],origin=(.025,.08,0.)))
    with pytest.raises(NumericalAmbiguityError,match="near-launch|zero-distance"):
        run(scene([element("D","receiver",(0.,.08,0.))]))
    boundary=element("boundary","receiver",(0.,.08,.75),aperture={"kind":"disk","radius_m":.25})
    with pytest.raises(ValueError,match="strictly inside"):
        validate_scene(scene([boundary]))


def test_full_63_branch_capacity_accounts_for_all_queued_and_current_weight():
    result = run(scene([element("plus", "ideal_splitter_50_50", (0., .08, .1)),
                        element("minus", "ideal_splitter_50_50", (0., .08, -.1))]))
    assert len(result.branches) == 63
    assert any(t["reason"] == "branch_cap" for t in result.terminals)
    assert result.ledger["truncated_weight"] > 0.
    assert result.ledger["absorbed_weight"] == result.ledger["detected_weight"] == 0.
    assert_ledger(result)


def _returning_split_loop():
    # Two opposite five-edge loops. Four finite mirrors between splitter
    # visits make the actual 256 combined-record limit bind before branch63.
    positive = [(0., 0.), (.3, 0.), (.3, .2), (.2, .3), (0., .3), (0., 0.)]
    mirrors = []
    for sign in (1., -1.):
        vertices = [(sign*x, sign*z) for x, z in positive]
        for i in range(1, 5):
            prev, current, following = vertices[i-1], vertices[i], vertices[i+1]
            incoming = np.array(current)-prev
            outgoing = np.array(following)-current
            incoming /= np.linalg.norm(incoming)
            outgoing /= np.linalg.norm(outgoing)
            normal = incoming-outgoing
            normal /= np.linalg.norm(normal)
            angle = math.atan2(float(normal[0]), float(normal[1]))
            mirrors.append(element(f"M{'p' if sign>0 else 'n'}{i}", "mirror", (current[0], .08, current[1]), angle))
    splitter = element("S", "ideal_splitter_50_50", (0., .08, 0.), -math.pi/4)
    return scene([splitter, *mirrors], origin=(0., .08, -.05))


def test_actual_full_256_combined_record_limit_returns_incomplete_with_complete_ledger():
    result = run(_returning_split_loop())
    assert len(result.segments)+len(result.hits) == 256
    assert any(t["reason"] == "record_cap" for t in result.terminals)
    assert len(result.branches) < 63
    assert result.ledger["truncated_weight"] == 1.
    assert_ledger(result)


@pytest.mark.parametrize("path,value,error", [
    (("source", "direction"), [0., 0., 0.], ValueError),
    (("source", "direction"), [0., 0., 2.], ValueError),
    (("source", "direction"), [True, 0., 1.], TypeError),
    (("source", "origin_m"), [0., math.nan, 0.], ValueError),
    (("source", "origin_m"), [0., math.inf, 0.], ValueError),
    (("source", "origin_m"), [11., 0., 0.], ValueError),
    (("source", "direction"), [0., 1.], ValueError),
    (("source", "relative_weight"), .5, ValueError),
    (("source", "id"), "other", ValueError),
    (("schema_version",), True, TypeError),
    (("schema_version",), 2, ValueError),
    (("model_contract",), "v0_aligned_scalar_forward_v1", ValueError),
])
def test_invalid_scene_is_not_repaired(path, value, error):
    draft = scene()
    target = draft
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(error):
        validate_scene(draft)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(extra=True),
    lambda d: d["source"].update(extra=True),
    lambda d: d["elements"][0].update(extra=True),
    lambda d: d["elements"][0]["pose"].update(extra=True),
    lambda d: d["elements"][0]["aperture"].update(extra=True),
    lambda d: d["elements"][0].update(id="source"),
    lambda d: d["elements"][0].update(id="invalid id"),
    lambda d: d["elements"][0].update(kind="lens"),
    lambda d: d["elements"][0]["pose"].update(rotation_xyz_rad=[0., 4., 0.]),
    lambda d: d["elements"][0]["aperture"].update(radius_m=0.),
    lambda d: d["elements"][0]["aperture"].update(radius_m=.3),
    lambda d: d["elements"][0]["pose"].update(position_m=[0., .08, .99]),
])
def test_closed_records_finite_dimensions_and_complete_aperture_admission(mutation):
    draft = folded()
    mutation(draft)
    with pytest.raises((TypeError, ValueError)):
        validate_scene(draft)


def test_all_declared_elements_validate_even_when_not_hit():
    draft = folded()
    draft["elements"].append(element("bad", "mirror", (.2, .08, .1), angles=(0., math.nan, 0.)))
    with pytest.raises(ValueError, match="finite"):
        validate_scene(draft)
    too_many = [element(f"D{i}", "receiver", (0., .08, .1+i*.01)) for i in range(17)]
    with pytest.raises(ValueError, match="maximum16"):
        validate_scene(scene(too_many))


def test_immutable_owned_scene_results_and_caller_floating_settings():
    draft = folded(True)
    original = deepcopy(draft)
    old = np.seterr(all="raise")
    try:
        owned = validate_scene(draft)
        result = trace_routes(owned)
        assert np.geterr() == {key: "raise" for key in old}
    finally:
        np.seterr(**old)
    assert draft == original
    draft["elements"][0]["pose"]["position_m"][0] = 8.
    assert owned.to_dict() == original and result.scene.to_dict() == original
    copy = result.to_dict()
    copy["hits"][0]["position_m"][0] = 8.
    assert result.hits[0]["position_m"][0] == 0.
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.status = "invented"
    with pytest.raises(TypeError):
        result.hits[0]["position_m"][0] = 8.


def test_validation_has_no_trace_and_revalidates_owned_scene(monkeypatch):
    monkeypatch.setattr(routing, "trace_routes", lambda value: pytest.fail("validation called trace"))
    owned = validate_scene(folded())
    assert validate_scene(owned).to_dict() == owned.to_dict()


def test_direct_trace_requires_public_scene_type():
    with pytest.raises(TypeError, match="GeometricScene"):
        trace_routes(folded())
