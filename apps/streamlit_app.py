"""Local M6 workbench. Launch from the checkout with ``python -m streamlit``."""
from __future__ import annotations

from pathlib import Path
import sys

# Streamlit executes a path as a script. Locate sibling app modules without an
# undocumented PYTHONPATH requirement or changing the installed core package.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).absolute().parent.parent))

try:
    import streamlit as st
except ModuleNotFoundError as exc:
    if exc.name != "streamlit":
        raise
    raise SystemExit(
        "The local workbench requires the optional UI dependencies, including "
        "streamlit==1.64.0. See README.md: Local holographic workbench. "
        "Use the approved project environment; no automatic installation occurs."
    ) from exc

from apps import presentation
from apps import workbench as wb

REPO_ROOT = Path(__file__).absolute().parent.parent
RUNS_ROOT = REPO_ROOT / "runs"


def _state() -> wb.WorkbenchState:
    """Return this browser session's controller state; never start an action."""
    if "workbench" not in st.session_state:
        st.session_state["workbench"] = wb.WorkbenchState()
    if "pending_ui_action" not in st.session_state:
        st.session_state["pending_ui_action"] = None
    return st.session_state["workbench"]


def _draft_from_widgets() -> wb.RunDraft:
    """Snapshot current widget values, including actual uploaded bytes."""
    state = st.session_state
    target_kind = state.get("draft_target_kind", "builtin")
    upload = state.get("draft_upload") if target_kind == "upload" else None
    return wb.RunDraft(
        target_kind=target_kind,
        ny=64 if target_kind == "builtin" else state.get("draft_ny", 64),
        nx=64 if target_kind == "builtin" else state.get("draft_nx", 64),
        dy_um=state.get("draft_dy_um", 8.0),
        dx_um=state.get("draft_dx_um", 8.0),
        wavelength_nm=state.get("draft_wavelength_nm", 633.0),
        distance_mm=state.get("draft_distance_mm", 5.0),
        iterations=state.get("draft_iterations", 50),
        seed=state.get("draft_seed", 0),
        psnr_data_range=state.get("draft_psnr_data_range", 1.0),
        upload_bytes=None if upload is None else upload.getvalue(),
        upload_name=None if upload is None else upload.name,
    )


def _submit_generate(nonce: str) -> None:
    """Accept only the offer captured by the button that sent this event."""
    state = _state()
    if st.session_state["pending_ui_action"] is not None:
        return
    if wb.submit_generate(state, _draft_from_widgets(), offered_nonce=nonce, runs_root=RUNS_ROOT):
        st.session_state["diagnostic_enabled"] = False


def _selected_text() -> str:
    explicit = st.session_state.get("bundle_path_input", "").strip()
    selection = explicit or st.session_state.get("bundle_choice", "")
    bundle = _state().bundle
    return selection or (str(bundle.path) if bundle is not None else "")


def _selection_changed() -> None:
    """Changing the selected bundle revokes the explicit diagnostic opt-in."""
    st.session_state["diagnostic_enabled"] = False
    _state().diagnostic_enabled = False


def _queue_existing(action: str, nonce: str) -> None:
    """Capture one UI request; execution occurs after disabled controls render."""
    state = _state()
    if state.busy or st.session_state["pending_ui_action"] is not None or nonce != state.offered_nonce:
        return
    diagnostic = action == "diagnostic" and st.session_state.get("diagnostic_enabled", False)
    if action == "diagnostic" and not diagnostic:
        return
    st.session_state["pending_ui_action"] = (action, nonce, _selected_text(), diagnostic)


def _render_draft(state: wb.WorkbenchState, disabled: bool) -> wb.RunDraft:
    with st.sidebar:
        st.header("建立實驗 Create")
        st.selectbox("目標來源 Target", ["builtin", "upload"],
                     format_func=lambda value: {"builtin": "固定光斑 · 64 × 64", "upload": "上傳灰階 PNG"}[value],
                     key="draft_target_kind", disabled=disabled)
        if st.session_state["draft_target_kind"] == "upload":
            st.file_uploader("8-bit 灰階 PNG", type=["png"], key="draft_upload",
                             max_upload_size=8, disabled=disabled)
            c1, c2 = st.columns(2)
            c1.number_input("列數 ny", min_value=1, max_value=512, value=64, step=1,
                            key="draft_ny", disabled=disabled)
            c2.number_input("欄數 nx", min_value=1, max_value=512, value=64, step=1,
                            key="draft_nx", disabled=disabled)
            st.caption("僅接受靜態 8-bit 灰階、尺寸完全相符的 PNG；不縮放、不轉色、不裁切。上限 8 MiB。")
        else:
            st.caption("固定 64 × 64 像素；光斑寬度 σ = 7.5 pixels。僅在 8 μm pitch 時對應 60 μm；修改 pitch 不改變像素值。")
        c1, c2 = st.columns(2)
        c1.number_input("dy (μm)", min_value=0.0, value=8.0, step=0.5, format="%.6f",
                        key="draft_dy_um", disabled=disabled)
        c2.number_input("dx (μm)", min_value=0.0, value=8.0, step=0.5, format="%.6f",
                        key="draft_dx_um", disabled=disabled)
        st.number_input("波長 Wavelength (nm)", min_value=0.0, value=633.0,
                        key="draft_wavelength_nm", disabled=disabled)
        st.number_input("傳播距離 Distance (mm)", value=5.0, step=0.5,
                        key="draft_distance_mm", disabled=disabled)
        c1, c2 = st.columns(2)
        c1.number_input("迭代數 Iterations", min_value=0, max_value=200, value=50, step=1,
                        key="draft_iterations", disabled=disabled)
        c2.number_input("Seed", min_value=0, max_value=2**32-1, value=0, step=1,
                        key="draft_seed", disabled=disabled)
        st.number_input("PSNR data_range", min_value=0.0, value=1.0,
                        key="draft_psnr_data_range", disabled=disabled,
                        help="明確的強度參考範圍；不是圖像顯示上限。必須大於零。")
        st.caption("每次明確設定與目標等功率的均勻照明。草稿更動不會計算或儲存。")
        st.button("產生並儲存 Generate & Save", type="primary", width="stretch",
                  key=f"generate_{state.offered_nonce}", disabled=disabled,
                  on_click=_submit_generate, args=(state.offered_nonce,))
        st.caption("App 限制：每邊 1–512、N ≤ 200；ny × nx × max(1,N) ≤ 13,107,200。這些限制不保證光學取樣足夠。")
    return _draft_from_widgets()


def _render_existing(state: wb.WorkbenchState, disabled: bool) -> None:
    replay_disabled = disabled or (
        state.bundle is not None and wb.bundle_operating_limit(state.bundle) is not None
    )
    with st.expander("開啟、驗證與重播 Open · Verify · Replay", expanded=True):
        candidates = [str(p) for p in wb.list_bundle_candidates(runs_root=RUNS_ROOT)]
        choices = [""] + candidates
        current_choice = st.session_state.get("bundle_choice", "")
        if current_choice and current_choice not in choices:
            choices.append(current_choice)
        left, right = st.columns(2)
        left.selectbox("既有實驗（清單不代表已驗證）", choices,
                       format_func=lambda value: "目前顯示的實驗（若有）" if not value else str(Path(value).relative_to(RUNS_ROOT)),
                       key="bundle_choice", on_change=_selection_changed, disabled=disabled)
        right.text_input("或輸入 runs/ 下的 bundle 路徑", key="bundle_path_input",
                         on_change=_selection_changed, disabled=disabled,
                         help="例如 m5/run-id，或 runs/ 內的完整路徑。有文字時優先使用此路徑；不接受外部路徑、連結或 junction。")
        a, b, c = st.columns(3)
        nonce = state.offered_nonce
        a.button("開啟 Open", key=f"open_{nonce}", on_click=_queue_existing,
                 args=("open", nonce), disabled=disabled, width="stretch")
        b.button("重新驗證並載入 Refresh", key=f"refresh_{nonce}", on_click=_queue_existing,
                 args=("refresh", nonce), disabled=disabled, width="stretch")
        c.button("嚴格重播 Strict replay", key=f"strict_{nonce}", on_click=_queue_existing,
                 args=("strict", nonce), disabled=replay_disabled, width="stretch")
        st.checkbox("明確啟用 diagnostic replay（不提升 qualification）",
                    key="diagnostic_enabled", disabled=disabled)
        state.diagnostic_enabled = st.session_state["diagnostic_enabled"]
        st.button("執行診斷重播 Diagnostic replay", key=f"diagnostic_{nonce}",
                  on_click=_queue_existing, args=("diagnostic", nonce),
                  disabled=replay_disabled or not state.diagnostic_enabled)
        st.caption("路徑與清單皆空白時，使用目前顯示的 bundle。開啟／刷新只檢查完整性，不自動重播。Strict replay 不符合來源／環境資格時維持 not_run。檔案不是持續監控；狀態屬於上次操作。")


def _execute_request(state: wb.WorkbenchState) -> bool:
    """Execute an already accepted action once; no action on ordinary reruns."""
    if state.pending is not None:
        with st.spinner("驗證目標 → 設定照明 → 計算並儲存 M5 bundle…"):
            wb.execute_pending_run(state)
        return True
    pending = st.session_state["pending_ui_action"]
    if pending is None:
        return False
    st.session_state["pending_ui_action"] = None
    action, nonce, selection, diagnostic = pending
    with st.spinner("檢查 bundle 並執行所選操作…"):
        if action == "open":
            wb.open_bundle(state, selection, runs_root=RUNS_ROOT, offered_nonce=nonce)
        elif action == "refresh":
            wb.reverify_bundle(state, selection, runs_root=RUNS_ROOT, offered_nonce=nonce)
        else:
            wb.replay_bundle(state, selection, runs_root=RUNS_ROOT, offered_nonce=nonce,
                             diagnostic=diagnostic)
    return True


def _render_result(state: wb.WorkbenchState, draft: wb.RunDraft) -> None:
    if state.error:
        st.error(state.error)
    if state.bundle is None:
        st.info("設定左側草稿後按「產生並儲存」，或開啟既有 bundle。重新整理瀏覽器不會自動執行。")
        return
    bundle = state.bundle
    st.subheader("已儲存結果 Saved result")
    st.code(str(bundle.path), language=None)
    if state.submitted is not None:
        st.caption(f"Submitted ID: {state.submitted.token} · Upload SHA-256: {state.submitted.upload_sha256 or 'built-in raster'}")
        if wb.draft_fingerprint(draft) != state.submitted.draft_fingerprint:
            st.warning("目前草稿不同；下方仍是上次提交的已儲存結果。Previous submission — saved settings retained.")
    else:
        st.caption("已載入 bundle；以下設定與陣列均來自此 bundle，與左側草稿無關。")
    a, b, c = st.columns(3)
    a.metric("完整性 Integrity", state.integrity)
    b.metric("資格 Qualification", state.qualification)
    c.metric("數值比較 Comparison", state.comparison)
    st.caption(f"Last operation: {state.last_operation} · {state.last_operation_at} · {state.last_operation_path}")
    if state.replay_report is not None:
        if state.replay_report.qualification_reasons:
            st.warning("資格未通過：" + "; ".join(state.replay_report.qualification_reasons))
        with st.expander("重播檢查細節 Replay checks"):
            st.json(dict(state.replay_report.checks))
            st.json({"recorded_source": dict(state.replay_report.recorded_source),
                     "current_source": dict(state.replay_report.current_source)})
    limit = wb.bundle_operating_limit(bundle)
    if limit:
        st.warning("有效 bundle 超出本 App 操作限制；停用數值圖像與重播。" + limit)
        with st.expander("已儲存設定與來源 Saved settings & provenance"):
            st.json(bundle.config.to_dict())
            st.json(bundle.software)
        return
    if state.presentation_error:
        st.error("儲存／載入已成功，但呈現失敗。完成的 bundle 已保留；不會自動重新產生。請選擇此路徑並按 Refresh。 " + state.presentation_error)
        return
    try:
        summary = presentation.summarize_bundle(arrays=bundle.arrays, config=bundle.config, metrics=bundle.metrics)
        images, history = presentation.build_result_figures(arrays=bundle.arrays)
        st.pyplot(images, width="stretch")
        images.clear()
        st.caption(f"Target / reconstruction 共用顯示範圍 [0, {summary['display']['intensity_max']:.8g}]，包含 overshoot；未獨立正規化。Phase 固定 [-π, +π] rad，是理想數值相位，不是校準後的 SLM 驅動圖。")
        st.pyplot(history, width="stretch")
        history.clear()
        st.caption("完整 M3 amplitude residual（N+1 點、線性座標）；不是 intensity NMSE，也不是百分比準確率。")
        st.subheader("已儲存量測 Metrics")
        for metric in summary["metrics"]:
            parameters = metric["parameters"]
            st.write(f"**{metric['name']}**: {metric['display_value']} · parameters: `{parameters}`")
            if metric["mask_role"]:
                st.caption(f"{metric['mask_role']}: {metric['selected_pixels']} selected pixels")
        illumination = summary["illumination"]
        st.write(f"**照明 Illumination**: {illumination['kind']} · amplitude min/max = "
                 f"{illumination['amplitude_min']:.8g} / {illumination['amplitude_max']:.8g}")
        st.write(f"**P_source** = {illumination['prescribed_source_power_au_m2']:.12g} a.u.·m² · "
                 f"**P_target** = {illumination['target_amplitude_power_au_m2']:.12g} a.u.·m²")
        with st.expander("已儲存設定與來源 Saved settings & provenance"):
            st.json(bundle.config.to_dict())
            st.json(bundle.software)
        st.caption("單一平面、完整週期性且無消逝波的 M3 模型；等功率不保證精確合成。Integrity 是相對於未簽章 manifest 的檢查，不是作者認證。")
    except Exception as exc:
        wb.record_presentation_failure(state, exc)
        st.error("儲存／載入已成功，但呈現失敗。完成的 bundle 已保留；不會自動重新產生。請選擇上方路徑並按 Refresh。 " + str(exc))


def main() -> None:
    """Render a thin one-page interface; all scientific actions are explicit."""
    st.set_page_config(page_title="Open Holographic Lab", page_icon="🔬", layout="wide")
    state = _state()
    disabled = state.busy or st.session_state["pending_ui_action"] is not None
    st.title("全像重建工作台")
    st.caption("Open Holographic Lab · 單平面相位合成與可重現實驗 · Local workbench")
    draft = _render_draft(state, disabled)
    _render_existing(state, disabled)
    if _execute_request(state):
        st.rerun()
    _render_result(state, draft)
    st.caption("僅供本機軟體實驗。每次操作只保證目前 session 內的重複事件防護；重新載入、崩潰或多個 session 不具持久 exactly-once 保證。")


if __name__ == "__main__":
    main()
