"""Narrow public composition permissions and passive import checks."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/"apps"/"virtual_bench"
MARKER="V2G_PUBLIC_BOUNDARY_DETECTED"
PUBLIC={
    "ohlab.optics":{"SequentialExperiment","sample_source"},
    "ohlab.optics.polarization":{"JonesField","apply_linear_polarizer","transmission_ratio"},
    "ohlab.optics.polarized_interference":{"PolarizerAction","RetarderAction","PolarizationArm",
        "PolarizedTwoArmSpec","PolarizedTwoArmResult","run_polarized_two_arm"},
}


def assert_public_boundary(source,filename="polarized_two_path_adapter.py"):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Import):
            assert all(not a.name.startswith("ohlab") and a.name.split(".")[0] not in
                {"importlib","scipy","matplotlib","PIL","streamlit"} for a in node.names),MARKER
        if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith("ohlab"):
            assert filename=="polarized_two_path_adapter.py" and node.level==0 and node.module in PUBLIC,MARKER
            assert all(a.name in PUBLIC[node.module] and a.asname in (None,a.name) for a in node.names),MARKER
        if isinstance(node,ast.Name):
            assert node.id not in {"eval","exec","__import__","import_module","mix_balanced","mix_balanced_jones",
                "run_two_arm","run_experiment","propagate_angular_spectrum","_norm","_geometry"},MARKER
        if isinstance(node,ast.Attribute):
            assert node.attr not in {"fft","fft2","ifft2","ifft","propagate_angular_spectrum","gerchberg_saxton",
                "mix_balanced","mix_balanced_jones","cos","sin","exp","sqrt"},MARKER


def test_new_adapter_exact_public_symbols_no_replacement_equations_and_protocol_no_science():
    assert_public_boundary((BACKEND/"polarized_two_path_adapter.py").read_text(encoding="utf-8"))
    assert_public_boundary((BACKEND/"polarized_two_path_protocol.py").read_text(encoding="utf-8"),"polarized_two_path_protocol.py")
    tree=ast.parse((BACKEND/"polarized_two_path_adapter.py").read_text(encoding="utf-8"))
    counts={name:sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==name for n in ast.walk(tree))
        for name in ("sample_source","run_polarized_two_arm","apply_linear_polarizer")}
    assert counts=={"sample_source":1,"run_polarized_two_arm":1,"apply_linear_polarizer":1}
    from_scalar=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="from_scalar"]
    assert len(from_scalar)==1


@pytest.mark.parametrize("source",[
    "from ohlab.optics.polarized_interference import mix_balanced_jones",
    "from ohlab.optics.polarized_interference import _ratio",
    "from ohlab.optics.polarized_interference import *",
    "from ohlab.optics import run_experiment",
    "from ohlab.optics.polarization import apply_linear_retarder",
    "from ohlab.optics.polarized_interference import run_polarized_two_arm as scalar",
    "import ohlab.optics.polarized_interference", "import importlib", "eval('1')", "__import__('ohlab')",
    "x.fft2(data)","math.cos(theta)",
])
def test_guard_detects_unapproved_private_alias_dynamic_and_replacement_access(source):
    with pytest.raises(AssertionError,match=MARKER):assert_public_boundary(source)


@pytest.mark.parametrize("filename",["server.py","protocol.py","polarized_two_path_protocol.py","unrelated.py"])
@pytest.mark.parametrize("source",[
    "from ohlab.optics.polarized_interference import run_polarized_two_arm",
    "from ohlab.optics.polarization import apply_linear_polarizer",
])
def test_new_permission_is_not_wildcarded_to_server_protocol_or_unrelated_files(filename,source):
    with pytest.raises(AssertionError,match=MARKER):assert_public_boundary(source,filename)


def test_new_adapter_protocol_document_imports_independently_and_passively():
    source=textwrap.dedent('''
        import importlib.abc, sys, socket, threading
        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'starlette','uvicorn','streamlit','PIL','matplotlib'}:
                    raise AssertionError('unexpected optional import: '+fullname)
        sys.meta_path.insert(0,Blocker())
        def forbidden(*a,**k):raise AssertionError('active import')
        socket.socket.bind=forbidden
        socket.socket.listen=forbidden
        threading.Thread.start=forbidden
        import apps.virtual_bench.polarized_two_path_adapter
        import apps.virtual_bench.polarized_two_path_protocol
        import apps.virtual_bench.experiment_documents
        assert 'apps.virtual_bench.server' not in sys.modules
        print('V2g public composition and document imports are passive')
    ''')
    environment=os.environ.copy();environment["PYTHONDONTWRITEBYTECODE"]="1"
    result=subprocess.run([sys.executable,"-B","-X","utf8","-c",source],cwd=ROOT,env=environment,
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_document_guard_rejects_new_compute_private_gate_and_disk_access():
    from test_virtual_bench_document_architecture import assert_validation_boundary,MARKER as document_marker
    for source in ("from .polarized_two_path_adapter import run_polarized_two_arm",
        "from .polarized_two_path_adapter import simulate_submission",
        "from .polarized_two_path_adapter import _incident", "from .polarized_two_path_protocol import encode_result",
        "x.run_polarized_two_arm(None)","x.submit(None)","x.release()","open('a.json')"):
        with pytest.raises(AssertionError,match=document_marker):assert_validation_boundary(source)
