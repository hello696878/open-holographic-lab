"""Exact W2 public boundary and detecting controls; old guards stay intact."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

import test_virtual_bench_architecture as legacy

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps/virtual_bench"
MARKER = "W2_EXACT_PUBLIC_BOUNDARY_DETECTED"
PUBLIC = {"GeometricScene", "GeometricTraceResult", "NumericalAmbiguityError",
          "UnsupportedNumericalInputError", "trace_routes", "validate_scene"}


def assert_boundary(source, filename):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            assert all(not item.name.startswith("ohlab") and item.name.split(".")[0] not in
                {"importlib","scipy","matplotlib","PIL","streamlit"} for item in node.names), MARKER
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert filename == "geometric_routing_adapter.py" and node.module == "ohlab.optics.geometric_routing" and node.level == 0, MARKER
            assert all(item.name in PUBLIC and item.asname in (None,item.name) for item in node.names), MARKER
        if isinstance(node, ast.Name):
            assert node.id not in {"eval","exec","__import__","import_module","getattr","setattr",
                "run_experiment","sample_source","apply_component","propagate_angular_spectrum"}, MARKER
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"fft","fft2","ifft","ifft2","sin","cos","tan","asin","acos",
                "intersect","reflect","run_experiment","propagate_angular_spectrum"}, MARKER


def test_public_adapter_has_one_runner_and_protocol_has_no_science_import():
    for filename in ("geometric_routing_adapter.py","geometric_routing_protocol.py"):
        source = (BACKEND/filename).read_text(encoding="utf-8")
        assert_boundary(source, filename)
        calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Call)
                 and isinstance(node.func,ast.Name) and node.func.id=="trace_routes"]
        assert len(calls) == (1 if filename.endswith("adapter.py") else 0)
    source = (ROOT/"tests/test_virtual_bench_architecture.py").read_text(encoding="utf-8")
    assert '{"wave_field_adapter.py", "wave_field_protocol.py"}' in source
    assert '{"ohlab.optics.wave_field"}' in source
    assert 'node.attr not in {"fft", "fft2", "ifft2", "propagate_angular_spectrum", "gerchberg_saxton"}' in source


@pytest.mark.parametrize("source,filename", [
    ("from ohlab.optics.geometric_routing import *","geometric_routing_adapter.py"),
    ("from ohlab.optics.geometric_routing import _intersect","geometric_routing_adapter.py"),
    ("from ohlab.optics.geometric_routing import trace_routes as other","geometric_routing_adapter.py"),
    ("from ohlab.optics.geometric_routing import trace_routes","geometric_routing_protocol.py"),
    ("from ohlab.optics.geometric_routing import GeometricScene","server.py"),
    ("import ohlab.optics.geometric_routing","geometric_routing_adapter.py"),
    ("import importlib","geometric_routing_protocol.py"),
    ("math.cos(1)","geometric_routing_adapter.py"),
    ("x.reflect(d,n)","geometric_routing_protocol.py"),
    ("getattr(x,'trace_routes')","geometric_routing_adapter.py"),
])
def test_new_boundary_control_rejects_private_dynamic_formula_and_wrong_owner(source,filename):
    with pytest.raises(AssertionError, match=MARKER):
        assert_boundary(source,filename)


def test_global_old_guard_allows_only_exact_new_adapter(monkeypatch,tmp_path):
    import shutil
    target=tmp_path/"backend"
    target.mkdir()
    shutil.copyfile(BACKEND/"adapter.py",target/"adapter.py")
    monkeypatch.setattr(legacy,"BACKEND",target)
    path=target/"geometric_routing_adapter.py"
    path.write_text("from ohlab.optics.geometric_routing import GeometricScene\n",encoding="utf-8")
    legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()
    for filename in ("geometric_routing_protocol.py","server.py","unrelated.py"):
        wrong=target/filename
        wrong.write_text("from ohlab.optics.geometric_routing import GeometricScene\n",encoding="utf-8")
        with pytest.raises(AssertionError):
            legacy.test_backend_uses_public_optics_without_replacement_or_unrelated_science()
        wrong.unlink()


def test_new_modules_import_without_server_io_graphics_listener_or_thread():
    source=textwrap.dedent("""
        import importlib.abc,socket,sys,threading
        class Block(importlib.abc.MetaPathFinder):
            def find_spec(self,fullname,path=None,target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional '+fullname)
        sys.meta_path.insert(0,Block())
        def forbidden(*args,**kwargs): raise AssertionError('active import')
        socket.socket.bind=forbidden
        socket.socket.listen=forbidden
        threading.Thread.start=forbidden
        import apps.virtual_bench.geometric_routing_adapter
        import apps.virtual_bench.geometric_routing_protocol
        assert 'apps.virtual_bench.server' not in sys.modules
        print('W2_PUBLIC_PASSIVE_IMPORT_OK')
    """)
    environment=os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"]="1"
    result=subprocess.run([sys.executable,"-B","-X","utf8","-c",source],cwd=ROOT,
                          env=environment,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert "W2_PUBLIC_PASSIVE_IMPORT_OK" in result.stdout


def test_owned_controlled_child_reuses_one_factory_and_all_ten_original_workers():
    path=ROOT/"scripts/w2_controlled_acceptance_server.py"
    tree=ast.parse(path.read_text(encoding="utf-8"))
    assert not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
        and node.func.id in {"Route","ComputationGate","ThreadPoolExecutor"} for node in ast.walk(tree))
    factories=[node for node in ast.walk(tree) if isinstance(node,ast.Call)
               and isinstance(node.func,ast.Name) and node.func.id=="original_factory"]
    assert len(factories)==1
    assert {keyword.arg for keyword in factories[0].keywords}=={
        "assets_dir","worker","two_path_worker","sweep_worker","polarization_worker",
        "polarization_sweep_worker","polarized_two_path_worker","polarized_two_path_sweep_worker",
        "r03_ideal_worker","wave_field_worker","geometric_routing_worker"}
    source=textwrap.dedent("""
        import runpy,socket,threading
        def forbidden(*args,**kwargs):raise AssertionError('active controlled import')
        socket.socket.bind=forbidden
        socket.socket.listen=forbidden
        threading.Thread.start=forbidden
        runpy.run_path('scripts/w2_controlled_acceptance_server.py',run_name='w2_passive_test')
        print('W2_CONTROLLED_CHILD_PASSIVE_OK')
    """)
    result=subprocess.run([sys.executable,"-B","-X","utf8","-c",source],cwd=ROOT,
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert "W2_CONTROLLED_CHILD_PASSIVE_OK" in result.stdout


def test_controlled_child_path_preflight_rejects_existing_alias_escape_and_reparse(tmp_path,monkeypatch):
    import importlib.util
    import stat
    from types import SimpleNamespace
    path=ROOT/"scripts/w2_controlled_acceptance_server.py"
    spec=importlib.util.spec_from_file_location("w2_owned_control_test",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner=tmp_path/"owned"
    owner.mkdir()
    child=owner/"fresh"
    assert module._owned_path(child,owner,absent=True)==child
    for invalid in (owner,owner/".."/"escape",Path("relative")):
        with pytest.raises(ValueError):module._owned_path(invalid,owner,absent=True)
    child.mkdir()
    marker=child/"preserve.txt"
    marker.write_text("owned original",encoding="utf-8")
    with pytest.raises(ValueError):module._owned_path(child,owner,absent=True)
    original_lstat=Path.lstat
    def marked(candidate,*args,**kwargs):
        info=original_lstat(candidate,*args,**kwargs)
        if candidate==child:
            return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        return info
    with monkeypatch.context() as isolated:
        isolated.setattr(Path,"lstat",marked)
        with pytest.raises(ValueError,match="reparse"):
            module._owned_path(child/"new",owner,absent=True)
    assert marker.read_text(encoding="utf-8")=="owned original"
