# graph.py
# LangGraph Orchestrator that calls into lkk.py (your podcast engine) for LLM + TTS.
# Same CLI feel as lkk.py + live event stream + Mermaid export (+ optional Studio UI, no LangSmith needed)

import os, sys, re, json, uuid, asyncio, datetime, atexit, webbrowser, threading
from time import perf_counter
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict, Literal
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# ---- import your podcast engine (filename must be lkk.py) -----------------
try:
    import lkk as podcast
except Exception as e:
    print("❌ Could not import lkk.py. Make sure the file is named 'lkk.py' and fixes any syntax errors.")
    print("   Common fix in lkk.py: change  pitch = f\"{p-2%}\"  to  pitch = f\"{p-2}%\"  inside _inflect().")
    raise

# ---- LangGraph core -------------------------------------------------------
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# ---- Optional pretty console (falls back to plain prints if missing) -----
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
    _RICH = True
except Exception:
    _RICH = False
    class Console:
        def print(self, *a, **k): print(*a)
        def rule(self, *a, **k): print("-" * 50)
    class Table:
        def __init__(self, title=None): self.rows=[]; self.title=title
        def add_column(self, *a, **k): pass
        def add_row(self, *cols): self.rows.append(cols)
    class Progress:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *exc): pass
        def add_task(self, *a, **k): return 1
        def update(self, *a, **k): pass
    class BarColumn: ...
    class TimeElapsedColumn: ...
    class TimeRemainingColumn: ...
    class TextColumn:
        def __init__(self, *a, **k): pass

console = Console()

# ------------------------- temp tracking & cleanup -------------------------
TMP: List[str] = []
@atexit.register
def _cleanup():
    for p in TMP:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

# ------------------------- WebSocket Server for Real-time Updates ----------
try:
    import websockets
    _WEBSOCKETS_AVAILABLE = True
except ImportError:
    _WEBSOCKETS_AVAILABLE = False
    print("⚠️  websockets module not available. Real-time visualization disabled.")
    print("   Install with: pip install websockets")

# Global WebSocket connections
_websocket_connections = set()

# WebSocket server for real-time updates
async def websocket_server(websocket, path):
    _websocket_connections.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        _websocket_connections.remove(websocket)

async def broadcast_websocket_message(data):
    if not _websocket_connections:
        return
        
    message = json.dumps(data)
    for connection in _websocket_connections.copy():
        try:
            await connection.send(message)
        except Exception:
            _websocket_connections.remove(connection)

# Start WebSocket server in background
def start_websocket_server():
    if not _WEBSOCKETS_AVAILABLE:
        return
        
    async def server_main():
        server = await websockets.serve(websocket_server, "localhost", 8003)
        print(f"WebSocket server running on ws://localhost:8003")
        await server.wait_closed()
    
    # Run WebSocket server in background
    asyncio.create_task(server_main())

# ------------------------- Visualization Server ----------------------------
def start_visualization_server(html_content, port=8002):
    class VisualizationHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            else:
                super().do_GET()
    
    # Create a custom server that serves our HTML content
    server = HTTPServer(('localhost', port), VisualizationHandler)
    print(f"Visualization server running at http://localhost:{port}")
    
    # Run server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

# ------------------------- tiny helpers -----------------------------------
def ensure_complete_response(text: str) -> str:
    t = re.sub(r'[`*_#>]+', ' ', (text or "")).strip()
    t = re.sub(r'\s{2,}', ' ', t)
    if t and t[-1] not in {'.', '!', '?'}:
        t += '.'
    return t

def _graph_ascii_safe(compiled_graph, state: Dict[str, Any], filename_prefix: str) -> str:
    path = f"{filename_prefix}.txt"
    try:
        ascii_map = compiled_graph.get_graph().draw_ascii()
        with open(path, "w", encoding="utf-8") as f:
            f.write(ascii_map + "\n")
            f.write("\n--- state keys ---\n")
            f.write(", ".join(sorted(state.keys())) + "\n")
        print(f"Graph ASCII saved to: {path}")
        return path
    except Exception as e:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("ASCII visualization unavailable. Minimal summary:\n\n")
                f.write("Nodes: nexus_intro -> reco_intro -> stat_intro -> nexus_topic_intro -> (reco_turn <-> stat_turn)* -> nexus_outro -> END\n")
                f.write("\n--- state keys ---\n")
                f.write(", ".join(sorted(state.keys())) + "\n")
            print(f"(fallback) Graph summary saved to: {path}")
        except:
            print("ASCII visualization error:", e)
        return path

def _write_mermaid_bundle(compiled_graph, session_id: str) -> Optional[str]:
    try:
        mermaid = compiled_graph.get_graph().draw_mermaid()
    except Exception:
        return None
    
    # Create the HTML content
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>LangGraph · {session_id}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    body {{
      margin: 0;
      padding: 16px;
      font-family: system-ui;
      background: #0f172a;
      color: #f8fafc;
    }}
    .wrap {{
      max-width: 1200px;
      margin: auto;
    }}
    .status {{
      background: #1e293b;
      padding: 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }}
    .current-node {{
      color: #3b82f6;
      font-weight: bold;
    }}
    #updates {{
      max-height: 200px;
      overflow-y: auto;
      background: #1e293b;
      padding: 8px;
      border-radius: 4px;
      margin-top: 16px;
    }}
    .update {{
      margin: 4px 0;
      padding: 4px;
      border-left: 3px solid #3b82f6;
    }}
  </style>
</head>
<body>
<div class="wrap">
  <h3>LangGraph Diagram — {session_id}</h3>
  
  <div class="status">
    <h4>Current Status: <span id="current-status">Initializing</span></h4>
    <div id="updates"></div>
  </div>
  
  <div class="mermaid" id="mermaid-diagram">
    {mermaid}
  </div>
</div>

<script>
  mermaid.initialize({{startOnLoad: true, securityLevel: "loose", theme: "dark"}});
  
  // Function to update the visualization
  function updateStatus(nodeName, eventType) {{
    const statusEl = document.getElementById('current-status');
    const updatesEl = document.getElementById('updates');
    
    statusEl.textContent = nodeName || 'Processing';
    
    if (nodeName) {{
      const update = document.createElement('div');
      update.className = 'update';
      update.textContent = `[${{new Date().toLocaleTimeString()}}] ${{eventType.toUpperCase()}} - ${{nodeName}}`;
      updatesEl.appendChild(update);
      updatesEl.scrollTop = updatesEl.scrollHeight;
    }}
  }}
  
  // Set up WebSocket connection for real-time updates
  const ws = new WebSocket('ws://localhost:8003/');
  ws.onmessage = function(event) {{
    const data = JSON.parse(event.data);
    updateStatus(data.node, data.event);
  }};
  
  ws.onerror = function(error) {{
    console.log('WebSocket Error:', error);
  }};
  
  ws.onopen = function() {{
    console.log('WebSocket connection established');
  }};
</script>
</body>
</html>"""
    
    # Save HTML to file
    html_path = Path(f"graph_{session_id}.html")
    html_path.write_text(html, encoding="utf-8")
    
    # Start the visualization server
    start_visualization_server(html)
    
    try:
        webbrowser.open_new_tab(f"http://localhost:8002/")
    except Exception:
        pass
    
    return str(html_path)

def wav_len(path: str) -> float:
    try:
        with podcast.wave.open(path, "rb") as r:
            fr = r.getframerate() or 24000
            return r.getnframes() / float(fr)
    except:
        return 0.0

def write_master(segments: List[str], out_path: str) -> str:
    return podcast.write_master(segments, out_path)

# ------------------------- context helpers --------------------------------
def list_json_files() -> List[str]:
    return [p.name for p in Path(".").iterdir() if p.is_file() and p.suffix.lower() == ".json"]

def load_context(choice: str) -> tuple[str, dict]:
    return podcast.load_context(choice)

def infer_topic_from_metrics(context_text: str) -> str:
    m = re.findall(r'\"metric_name\"\s*:\s*\"([^\"]+)\"', context_text, flags=re.I)
    if m:
        sample = ", ".join(m[:3])
        return f"Trends in {sample}"
    pm = re.search(r'"previousMonthName"\s*:\s*"([^"]+)"', context_text)
    if pm:
        return f"{pm.group(1)} performance trends"
    return "Operational metrics analysis"

# ------------------------- graph state ------------------------------------
class PodcastState(TypedDict):
    messages: List[Dict[str, Any]]
    current_speaker: str
    topic: str
    context: Dict[str, Any]
    interrupted: bool
    audio_segments: List[str]
    conversation_history: List[Dict[str, str]]
    current_turn: float
    max_turns: int
    session_id: str
    node_history: List[Dict[str, Any]]
    current_node: str
    script_lines: List[str]

# ------------------------- nodes (use lkk for LLM+TTS) --------------------
async def _tts(text: str, role: str) -> str:
    ssml = podcast.text_to_ssml(text, role)
    path = await asyncio.to_thread(podcast.synth, ssml)
    TMP.append(path)
    return path

async def nexus_intro_node(state: PodcastState) -> Dict[str, Any]:
    line = podcast.NEXUS_INTRO
    audio = await _tts(line, "NEXUS")
    print("Nexus intro generated.")
    return {
        "messages": add_messages(state["messages"], [{"role": "system", "content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"NEXUS","text":line}],
        "script_lines": state["script_lines"] + [f"Agent Nexus:{line}"],
        "current_speaker": "RECO",
        "node_history": state["node_history"] + [{"node":"nexus_intro","ts": datetime.datetime.now().isoformat()}],
        "current_node": "nexus_intro"
    }

async def reco_intro_node(state: PodcastState) -> Dict[str, Any]:
    line = podcast.RECO_INTRO
    audio = await _tts(line, "RECO")
    print("Reco intro generated.")
    return {
        "messages": add_messages(state["messages"], [{"role": "system", "content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"RECO","text":line}],
        "script_lines": state["script_lines"] + [f"Agent Reco:{line}"],
        "current_speaker": "STAT",
        "node_history": state["node_history"] + [{"node":"reco_intro","ts": datetime.datetime.now().isoformat()}],
        "current_node": "reco_intro"
    }

async def stat_intro_node(state: PodcastState) -> Dict[str, Any]:
    line = podcast.STAT_INTRO
    audio = await _tts(line, "STAT")
    print("Stat intro generated.")
    return {
        "messages": add_messages(state["messages"], [{"role": "system", "content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"STAT","text":line}],
        "script_lines": state["script_lines"] + [f"Agent Stat:{line}"],
        "current_speaker": "NEXUS",
        "node_history": state["node_history"] + [{"node":"stat_intro","ts": datetime.datetime.now().isoformat()}],
        "current_node": "stat_intro"
    }

async def nexus_topic_intro_node(state: PodcastState) -> Dict[str, Any]:
    print("Generating Nexus topic introduction...")
    topic_line = await podcast.generate_nexus_topic_intro(state["context"]["summary"])
    topic_line = ensure_complete_response(topic_line)
    audio = await _tts(topic_line, "NEXUS")
    return {
        "messages": add_messages(state["messages"], [{"role": "system", "content": topic_line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"NEXUS","text":topic_line}],
        "script_lines": state["script_lines"] + [f"Agent Nexus:{topic_line}"],
        "current_speaker": "RECO",
        "current_turn": 0.0,
        "node_history": state["node_history"] + [{"node":"nexus_topic_intro","ts": datetime.datetime.now().isoformat()}],
        "current_node": "nexus_topic_intro"
    }

_last_openings: Dict[str, str] = {}

async def reco_turn_node(state: PodcastState) -> Dict[str, Any]:
    total_pairs = int(state["max_turns"])
    current_pair = int(state["current_turn"]) + 1
    print(f"Generating turn {current_pair}/{total_pairs}… (Reco)")
    last_stat = next((m for m in reversed(state["conversation_history"]) if m["speaker"]=="STAT"), None)
    prompt = (
        f"Context: {state['context'].get('summary','metrics')}.\n"
        f"Stat just said: '{last_stat['text'] if last_stat else ''}'. "
        f"ONE sentence; include one concrete recommendation or method; do not invent numbers."
    )
    line = await podcast.llm(podcast.SYSTEM_RECO, prompt)
    line = podcast.vary_opening(line, "RECO", _last_openings)
    line = podcast._add_conversation_dynamics(line, "RECO", "STAT", state["context"].get("summary",""), int(state['current_turn']), state["conversation_history"])
    line = podcast._clean_repetition(ensure_complete_response(line))
    audio = await _tts(line, "RECO")
    return {
        "messages": add_messages(state["messages"], [{"role":"system","content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"RECO","text": line}],
        "script_lines": state["script_lines"] + [f"Agent Reco:{line}"],
        "current_speaker": "STAT",
        "current_turn": state["current_turn"] + 0.5,
        "node_history": state["node_history"] + [{"node":"reco_turn","ts": datetime.datetime.now().isoformat()}],
        "current_node": "reco_turn"
    }

async def stat_turn_node(state: PodcastState) -> Dict[str, Any]:
    total_pairs = int(state["max_turns"])
    current_pair = int(state["current_turn"] + 0.5) + 1
    print(f"Generating turn {current_pair}/{total_pairs}… (Stat)")
    last_reco = next((m for m in reversed(state["conversation_history"]) if m["speaker"]=="RECO"), None)
    prompt = (
        f"Context: {state['context'].get('summary','metrics')}.\n"
        f"Reco just said: '{last_reco['text'] if last_reco else ''}'. "
        f"ONE sentence; add one concrete validation/check or risk and the immediate next step."
    )
    line = await podcast.llm(podcast.SYSTEM_STAT, prompt)
    line = podcast.vary_opening(line, "STAT", _last_openings)
    line = podcast._add_conversation_dynamics(line, "STAT", "RECO", state["context"].get("summary",""), int(state['current_turn']), state["conversation_history"])
    line = podcast._clean_repetition(ensure_complete_response(line))
    audio = await _tts(line, "STAT")
    next_speaker = "RECO" if state["current_turn"] + 0.5 < state["max_turns"] else "NEXUS"
    return {
        "messages": add_messages(state["messages"], [{"role":"system","content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"STAT","text": line}],
        "script_lines": state["script_lines"] + [f"Agent Stat:{line}"],
        "current_speaker": next_speaker,
        "current_turn": state["current_turn"] + 0.5,
        "node_history": state["node_history"] + [{"node":"stat_turn","ts": datetime.datetime.now().isoformat()}],
        "current_node": "stat_turn"
    }

async def nexus_outro_node(state: PodcastState) -> Dict[str, Any]:
    line = podcast.NEXUS_OUTRO
    audio = await _tts(line, "NEXUS")
    print("Nexus outro generated.")
    return {
        "messages": add_messages(state["messages"], [{"role": "system", "content": line}]),
        "audio_segments": state["audio_segments"] + [audio],
        "conversation_history": state["conversation_history"] + [{"speaker":"NEXUS","text": line}],
        "script_lines": state["script_lines"] + [f"Agent Nexus:{line}"],
        "current_speaker": "END",
        "node_history": state["node_history"] + [{"node":"nexus_outro","ts": datetime.datetime.now().isoformat()}],
        "current_node": "nexus_outro"
    }

# ------------------------- edges & compile --------------------------------
def should_continue(state: PodcastState) -> Literal["continue_conversation","end_conversation"]:
    return "end_conversation" if state["current_turn"] >= state["max_turns"] else "continue_conversation"

def _build_compiled_graph():
    builder = StateGraph(PodcastState)
    builder.add_node("nexus_intro",        nexus_intro_node)
    builder.add_node("reco_intro",         reco_intro_node)
    builder.add_node("stat_intro",         stat_intro_node)
    builder.add_node("nexus_topic_intro",  nexus_topic_intro_node)
    builder.add_node("reco_turn",          reco_turn_node)
    builder.add_node("stat_turn",          stat_turn_node)
    builder.add_node("nexus_outro",        nexus_outro_node)
    builder.set_entry_point("nexus_intro")
    builder.add_edge("nexus_intro", "reco_intro")
    builder.add_edge("reco_intro", "stat_intro")
    builder.add_edge("stat_intro", "nexus_topic_intro")
    builder.add_edge("nexus_topic_intro", "reco_turn")
    builder.add_conditional_edges("reco_turn", should_continue, {
        "continue_conversation": "stat_turn",
        "end_conversation": "nexus_outro",
    })
    builder.add_conditional_edges("stat_turn", should_continue, {
        "continue_conversation": "reco_turn",
        "end_conversation": "nexus_outro",
    })
    builder.add_edge("nexus_outro", END)
    return builder.compile()

# --- LangGraph Studio hook (local UI) ---
_STUDIO_AVAILABLE = False
_STUDIO_HANDLER = None
try:
    # studio callback, used to stream live node activation to LangGraph Studio
    from langgraph import StudioCallbackHandler  # langgraph>=0.2
    _STUDIO_AVAILABLE = True
except Exception:
    _STUDIO_AVAILABLE = False
    StudioCallbackHandler = None

# You can toggle Studio integration with this env var (1 = enabled, 0 = disabled)
_ENABLE_STUDIO = os.getenv("ENABLE_LANGGRAPH_STUDIO", "1").strip() not in {"0", "false", "False"}

def _maybe_create_studio_handler():
    global _STUDIO_HANDLER
    if _STUDIO_HANDLER is not None:
        return _STUDIO_HANDLER
    if _STUDIO_AVAILABLE and _ENABLE_STUDIO:
        try:
            _STUDIO_HANDLER = StudioCallbackHandler()
            console.print("[bold green]LangGraph Studio callback enabled.[/]" if _RICH else "LangGraph Studio callback enabled.")
            return _STUDIO_HANDLER
        except Exception as e:
            console.print(f"[bold yellow]Studio handler init failed:[/] {e}" if _RICH else f"Studio handler init failed: {e}")
            _STUDIO_HANDLER = None
            return None
    return None

# --- LangGraph Studio SqliteSaver hook (optional) ---
_STUDIO_SAVER_AVAILABLE = False
try:
    from langgraph.checkpoint.sqlite import SqliteSaver   # langgraph>=0.2
    _STUDIO_SAVER_AVAILABLE = True
except Exception:
    try:
        from langgraph.checkpoint import SqliteSaver      # some distros
        _STUDIO_SAVER_AVAILABLE = True
    except Exception:
        SqliteSaver = None                                # type: ignore
        _STUDIO_SAVER_AVAILABLE = False

def build_app():
    """Exposes `app` for `langgraph dev` (Studio UI)."""
    compiled = _build_compiled_graph()
    if _STUDIO_SAVER_AVAILABLE:
        try:
            checkpointer = SqliteSaver.from_conn_string("ui_checkpoints.sqlite")
            compiled = compiled.with_config(checkpointer=checkpointer)
        except Exception:
            pass
    return compiled

app = build_app()   # Studio looks for this symbol

# ------------------------- live event stream -------------------------------
async def _run_with_events(compiled_graph, initial, recursion_limit: int, session_id: str):
    """
    Stream LangGraph events to terminal and save TXT/JSONL timelines.
    Returns (final_state, timeline_txt_path).
    """
    timeline_path_txt = f"timeline_{session_id}.log"
    timeline_path_jsonl = f"timeline_{session_id}.jsonl"
    node_stats: Dict[str, Dict[str, Any]] = {}
    final_state: Optional[Dict[str, Any]] = None

    # possibly create studio handler for live visualization
    studio_handler = _maybe_create_studio_handler()

    console.rule("[bold cyan]Live LangGraph Events" if _RICH else "Live LangGraph Events")
    with open(timeline_path_txt, "w", encoding="utf-8") as log_txt, \
         open(timeline_path_jsonl, "w", encoding="utf-8") as log_jsonl, \
         Progress(
             TextColumn("[progress.description]{task.description}"),
             BarColumn(),
             "[progress.percentage]{task.percentage:>3.0f}%",
             TimeElapsedColumn(),
             TimeRemainingColumn(),
             transient=True,
         ) if _RICH else Progress() as progress:

        turns_task = None
        try:
            # include callbacks only if studio handler is available
            callbacks = [studio_handler] if studio_handler else None

            async for ev in compiled_graph.astream_events(
                initial, version="v1", config={"recursion_limit": recursion_limit}, callbacks=callbacks
            ):
                et = ev.get("event")
                name = ev.get("name") or ev.get("data", {}).get("name") or ev.get("metadata", {}).get("node")
                ts = datetime.datetime.now().isoformat(timespec="seconds")

                # Send WebSocket update for real-time visualization
                if _WEBSOCKETS_AVAILABLE:
                    await broadcast_websocket_message({
                        "node": name,
                        "event": et,
                        "timestamp": ts
                    })

                # plain text
                line = f"[{ts}] {et.replace('_',' ').upper()} - {name or '-'}\n"
                log_txt.write(line); log_txt.flush()

                # JSONL (safe)
                def _safe(obj):
                    try:
                        json.dumps(obj)
                        return obj
                    except Exception:
                        return str(obj)
                payload = { "ts": ts, "event": et, "name": name,
                            "data": {k: _safe(v) for k,v in (ev.get("data") or {}).items()} }
                log_jsonl.write(json.dumps(payload, ensure_ascii=False) + "\n")
                log_jsonl.flush()

                # pretty + timing
                if et in ("on_chain_start", "on_node_start"):
                    console.print(f"[bold green]► START[/] {name or '—'}" if _RICH else f"START {name or '—'}")
                    node_stats.setdefault(name or "—", {}).setdefault("count", 0)
                    node_stats[name or "—"]["count"] += 1
                    node_stats[name or "—"]["_t0"] = perf_counter()
                    if _RICH and name == "reco_turn" and turns_task is None:
                        max_pairs = int(initial.get("max_turns", 6))
                        turns_task = progress.add_task("Conversation turns", total=max_pairs*2)
                elif et in ("on_chain_end", "on_node_end"):
                    console.print(f"[bold yellow]✔ END[/]   {name or '—'}" if _RICH else f"END   {name or '—'}")
                    s = node_stats.get(name or "—", {})
                    if "_t0" in s:
                        dt = perf_counter() - s["_t0"]
                        s["elapsed"] = s.get("elapsed", 0.0) + dt
                        s["last_dt"] = dt
                        s.pop("_t0", None)
                    if _RICH and turns_task is not None and name in ("reco_turn", "stat_turn"):
                        progress.update(turns_task, advance=1)
                    out = ev.get("data", {}).get("output")
                    if out and isinstance(out, dict):
                        final_state = out  # keep latest output seen
                        last = out.get("conversation_history", [])[-1:] or []
                        for msg in last:
                            if isinstance(msg, dict) and "speaker" in msg and "text" in msg:
                                console.print(f"[dim]{msg['speaker']}:[/] {msg['text']}" if _RICH else f"{msg['speaker']}: {msg['text']}")

        except Exception as e:
            console.print(f"[bold red]Event stream error:[/] {e}" if _RICH else f"Event stream error: {e}")

    # Summary table
    table = Table(title="Node Summary")
    table.add_column("Node"); table.add_column("Calls", justify="right")
    table.add_column("Total s", justify="right"); table.add_column("Last s", justify="right")
    for node, s in node_stats.items():
        table.add_row(node, str(s.get("count", 0)),
                      f"{s.get('elapsed', 0.0):.2f}", f"{s.get('last_dt', 0.0):.2f}")
    console.print(table)

    # Event stream outputs can be trimmed; ensure we have full state with audio_segments.
    if not isinstance(final_state, dict) or "audio_segments" not in final_state:
        # If we have a studio handler, pass callbacks into ainvoke as well so Studio receives final node events
        try:
            if studio_handler:
                final_state = await compiled_graph.ainvoke(initial, config={"recursion_limit": recursion_limit}, callbacks=[studio_handler])
            else:
                final_state = await compiled_graph.ainvoke(initial, config={"recursion_limit": recursion_limit})
        except Exception as e:
            console.print(f"[bold red]ainvoke fallback failed:[/] {e}" if _RICH else f"ainvoke fallback failed: {e}")
            raise

    return final_state, timeline_path_txt

# ------------------------- main API ---------------------------------------
async def generate_podcast(topic: Optional[str] = None,
                           max_turns: int = 6,
                           file_choice: str = "both",
                           session_id: Optional[str] = None,
                           recursion_limit: int = 60) -> Dict[str, Any]:
    session_id = session_id or f"pod_{uuid.uuid4().hex[:8]}"
    context_text, meta = load_context(file_choice)
    resolved_topic = topic or infer_topic_from_metrics(context_text)

    initial: PodcastState = {
        "messages": [],
        "current_speaker": "NEXUS",
        "topic": resolved_topic,
        "context": {"summary": f"Files: {meta.get('files', [])}\n\n{context_text}"},
        "interrupted": False,
        "audio_segments": [],
        "conversation_history": [],
        "script_lines": [],
        "current_turn": 0.0,
        "max_turns": max_turns,
        "session_id": session_id,
        "node_history": [],
        "current_node": "start",
    }

    compiled_graph = _build_compiled_graph()
    structure_path = _graph_ascii_safe(compiled_graph, initial, f"structure_{session_id}")

    _write_mermaid_bundle(compiled_graph, session_id)  # .mmd + .html + auto-open

    # === run with live event stream ===
    final_state, timeline_path = await _run_with_events(compiled_graph, initial, recursion_limit, session_id)

    execution_path = _graph_ascii_safe(compiled_graph, final_state, f"execution_{session_id}")

    # Match lkk.py output file names
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_wav = f"podcast_{timestamp}.wav"

    # Guard against missing segments (shouldn't happen after the fix, but safe)
    segments = final_state.get("audio_segments", [])
    if not isinstance(segments, list):
        segments = []
    if segments:
        write_master(segments, out_wav)
    else:
        print("⚠️ No audio segments found; skipping master write.")

    script_file = f"podcast_script_{timestamp}.txt"
    with open(script_file, "w", encoding="utf-8") as f:
        f.write("\n".join(final_state.get("script_lines", [])))

    # Also keep a JSON log
    log_file = f"graph_convo_{session_id}.json"
    Path(log_file).write_text(json.dumps({
        "conversation_history": final_state.get("conversation_history", []),
        "node_history": final_state.get("node_history", []),
        "topic": resolved_topic,
        "turns": max_turns,
        "session_id": session_id,
        "files": meta.get("files", []),
    }, indent=2), encoding="utf-8")

    total_duration = sum(wav_len(p) for p in segments)

    # lkk-style success prints
    print("\nPodcast generated successfully!")
    print(f"Audio: {out_wav}")
    print(f"Script: {script_file}")

    return {
        "session_id": session_id,
        "topic": resolved_topic,
        "turns": max_turns,
        "audio_file": out_wav,
        "duration_seconds": round(total_duration, 2),
        "conversation_log": log_file,
        "graph_visualization": execution_path,
        "graph_structure": structure_path,
        "timeline": timeline_path,
        "success": True,
    }

# ------------------------- CLI (single input point) -----------------------
def _cli_choose_files() -> str:
    files = list_json_files()
    print("JSON files in folder:", files)
    print("Type one of: data.json, metric_data.json, both, then Enter:")
    choice = (sys.stdin.readline() or "").strip().lower()
    if choice not in {"data.json", "metric_data.json", "both"}:
        if "data.json" in files and "metric_data.json" in files:
            return "both"
        return files[0] if files else "both"
    return choice

async def _cli_main():
    print("🎧 LangGraph + lkk Orchestrator (single CLI)")
    print("=" * 50)
    
    # Start WebSocket server for real-time visualization
    start_websocket_server()
    
    choice = _cli_choose_files()
    topic = input("Enter topic (blank = infer from data): ").strip() or None
    try:
        turns = int(input("Enter number of conversation turns (2–12): ").strip() or "6")
        turns = max(2, min(12, turns))
    except:
        turns = 6
    try:
        recursion_limit = int(input("Recursion limit (Enter for 60): ").strip() or "60")
    except:
        recursion_limit = 60

    # Print Studio status (helps debugging why nodes may not appear)
    if _STUDIO_AVAILABLE and _ENABLE_STUDIO:
        console.print("[green]LangGraph Studio integration ENABLED.[/]" if _RICH else "LangGraph Studio integration ENABLED.")
        console.print("Run `langgraph studio` in another terminal to view the live UI." if _RICH else "Run `langgraph studio` in another terminal to view the live UI.")
    else:
        console.print("[yellow]LangGraph Studio integration DISABLED or not installed.[/]" if _RICH else "LangGraph Studio integration DISABLED or not installed.")
        console.print("Install with: pip install 'langgraph[studio]' and set ENABLE_LANGGRAPH_STUDIO=1." if _RICH else "Install with: pip install 'langgraph[studio]' and set ENABLE_LANGGRAPH_STUDIO=1.")

    print(f"\nGenerating with file_choice='{choice}', topic='{topic or 'auto'}', turns={turns}, recursion_limit={recursion_limit}…\n")
    result = await generate_podcast(topic, turns, file_choice=choice, recursion_limit=recursion_limit)

    print("\n✅ Podcast generation complete!")
    print(f"   Audio file:        {result['audio_file']}")
    print(f"   Duration (sec):    {result['duration_seconds']}")
    print(f"   Conversation log:  {result['conversation_log']}")
    print(f"   Graph structure:   {result['graph_structure']}")
    print(f"   Graph ASCII:       {result['graph_visualization']}")
    print(f"   Timeline:          {result['timeline']}")

if __name__ == "__main__":
    try:
        asyncio.run(_cli_main())
    except Exception as e:
        print("Error:", e)
        import traceback; traceback.print_exc()
