"""Live web dashboard (FastAPI + SSE).

Layout: a row of per-agent widgets (beat · phase · action · latest thought · digest),
a chat panel that renders routing ([A] -> [B] / -> all), and the ideas board.

Optional: only imported when --dashboard is passed, so the core run needs no web deps.
"""

from __future__ import annotations

import json
import threading
import time

from .types import to_jsonable

_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Think Tank — Research Panel</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
 header{padding:12px 18px;background:#171a21;font-weight:600;font-size:18px}
 #phase{color:#8ab4f8}
 .wrap{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px}
 .col{display:flex;flex-direction:column;gap:14px}
 .card{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:12px}
 .card h3{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:#9aa4b2}
 .agents{display:grid;grid-template-columns:1fr 1fr;gap:10px}
 .agent{min-width:0;overflow:hidden}
 .agent .beat{font-weight:600;overflow-wrap:anywhere}
 .agent .meta{font-size:12px;color:#8ab4f8;margin:2px 0;overflow-wrap:anywhere}
 .agent .thought{font-size:12px;color:#c8c8c8;font-style:italic;margin-top:4px;overflow-wrap:anywhere;max-height:72px;overflow:auto}
 .agent .digest{font-size:11px;color:#7f8896;white-space:pre-wrap;overflow-wrap:anywhere;margin-top:6px;max-height:120px;overflow:auto}
 #agents{max-height:52vh;overflow-y:auto;padding-right:4px}
 .msg{font-size:13px;margin:4px 0;line-height:1.35}
 .msg.human{background:#1f2733;border-radius:6px;padding:4px 6px}
 .msg .from{font-weight:600}
 .arrow{color:#6b7280}
 .msg .to{font-weight:600;color:#f0a0d0}
 .idea{font-size:13px;margin:8px 0;border-left:3px solid #8ab4f8;padding-left:8px}
 .idea .t{font-weight:600}
 .idea .b{font-size:11px;color:#9aa4b2}
 #chat{height:60vh;overflow:auto}
 .composer{display:flex;gap:6px;margin-top:10px}
 .composer select,.composer input{background:#0f1115;color:#e6e6e6;border:1px solid #262b36;border-radius:6px;padding:7px}
 .composer input{flex:1}
 .composer button{background:#2c6cf6;color:#fff;border:0;border-radius:6px;padding:7px 14px;cursor:pointer}
 .composer button:hover{background:#3b79ff}
</style></head>
<body>
<header>Think Tank — Cross-Domain Research Panel &nbsp; <span id="phase">starting…</span></header>
<div class="wrap">
 <div class="col">
   <div class="card"><h3>Agents</h3><div id="agents" class="agents"></div></div>
   <div class="card"><h3>Cross-Pollination Ideas</h3><div id="ideas"></div></div>
 </div>
 <div class="col">
   <div class="card"><h3>Chat</h3><div id="chat"></div>
     <div class="composer">
       <input id="say" placeholder="Message all agents… (Enter to send)" />
       <button id="send">Send</button>
     </div>
   </div>
 </div>
</div>
<script>
const colors={};const palette=["#8ab4f8","#f0b","#7ee787","#ffa657","#d2a8ff","#79c0ff"];
function colorFor(a){if(!(a in colors)){colors[a]=palette[Object.keys(colors).length%palette.length];}return colors[a];}
const agents={};
function renderAgents(){const el=document.getElementById('agents');el.innerHTML='';
 for(const k of Object.keys(agents).sort()){const a=agents[k];const d=document.createElement('div');
  d.className='agent card';d.style.borderColor=colorFor(k);
  d.innerHTML=`<div class="beat" style="color:${colorFor(k)}">${k}</div>
   <div class="meta">${a.phase||''} · ${a.action||''}</div>
   <div class="thought">${a.thought||''}</div>
   <div class="digest">${(a.digest||'').replace(/</g,'&lt;')}</div>`;el.appendChild(d);}}
function addMsg(from,to,text,human){const el=document.getElementById('chat');const d=document.createElement('div');
 d.className='msg'+(human?' human':'');const dest=to?to:'all';
 d.innerHTML=`<span class="from" style="color:${human?'#7ee787':colorFor(from)}">[${from}]</span>
  <span class="arrow">→</span> <span class="to">[${dest}]</span>: ${text.replace(/</g,'&lt;')}`;
 el.appendChild(d);el.scrollTop=el.scrollHeight;}

(function initComposer(){
 async function send(){const inp=document.getElementById('say');const text=inp.value.trim();
  if(!text)return;inp.value='';
  await fetch('/say',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({to:null,text})});}  // always broadcast to all
 document.getElementById('send').onclick=send;
 document.getElementById('say').addEventListener('keydown',e=>{if(e.key==='Enter')send();});
})();
async function refreshState(){const r=await fetch('/state');const s=await r.json();
 const el=document.getElementById('ideas');el.innerHTML='';
 for(const i of s.ideas){const d=document.createElement('div');d.className='idea';
  d.innerHTML=`<div class="t">${i.title}</div>
   <div class="b">[${i.beats.join(', ')}] · by ${i.author} · +${i.endorsements.length}</div>
   <div>${i.description.replace(/</g,'&lt;')}</div>`;el.appendChild(d);}
 for(const dg of s.digests){if(agents[dg.beat]){agents[dg.beat].digest=dg.content;}}
 renderAgents();}
const es=new EventSource('/events');
es.onmessage=(e)=>{const ev=JSON.parse(e.data);
 if(ev.type==='phase_start'){document.getElementById('phase').textContent='Round '+ev.round+' — '+ev.phase;}
 if(ev.type==='step'){const r=ev.result;const a=agents[r.agent]||(agents[r.agent]={});
  a.phase=r.phase;a.action=r.action;a.thought=r.thought;
  for(const m of r.messages_sent){addMsg(r.agent,m.to,m.text);}renderAgents();refreshState();}
 if(ev.type==='chat'){addMsg(ev.from,ev.to,ev.text,ev.human);}
 if(ev.type==='done'){document.getElementById('phase').textContent='complete';refreshState();}};
</script></body></html>
"""


class Dashboard:
    def __init__(self, port, agents, chat, ideas, digests):
        self.port = port
        self.agents = agents
        self.chat = chat
        self.ideas = ideas
        self.digests = digests
        self.beats = [a.id for a in agents]
        self._history: list[str] = []
        self._lock = threading.Lock()
        self._server = None
        self._start_server()

    def _start_server(self):
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, StreamingResponse

        app = FastAPI()
        page = _PAGE.replace("__BEATS__", json.dumps(self.beats))

        @app.get("/")
        def index():
            return HTMLResponse(page)

        @app.post("/say")
        async def say(payload: dict):
            to = payload.get("to") or None
            text = (payload.get("text") or "").strip()
            if not text:
                return {"ok": False}
            self.chat.post("You", to, text)  # human joins as a panelist
            self.push({"type": "chat", "from": "You", "to": to, "text": text, "human": True})
            # Trigger a live response: the addressed agent (or all, if broadcast).
            targets = [a for a in self.agents if to is None or a.id == to]
            threading.Thread(target=self._respond, args=(targets,), daemon=True).start()
            return {"ok": True, "responding": [a.id for a in targets]}

        @app.get("/state")
        def state():
            return {
                "ideas": to_jsonable(self.ideas.all()),
                "digests": to_jsonable(self.digests.read()),
            }

        @app.get("/events")
        def events():
            import asyncio

            async def gen():
                idx = 0
                while True:
                    with self._lock:
                        pending = self._history[idx:]
                        idx = len(self._history)
                    for item in pending:
                        yield f"data: {item}\n\n"
                    await asyncio.sleep(0.15)

            return StreamingResponse(gen(), media_type="text/event-stream")

        cfg = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self._server = uvicorn.Server(cfg)
        threading.Thread(target=self._server.run, daemon=True).start()
        time.sleep(0.4)  # let it bind before the run starts

    def _respond(self, targets):
        """Run a REPLY turn for each addressed agent (called off the request thread)."""
        for a in targets:
            try:
                r = a.step("REPLY")
                self.push({"type": "step", "round": "reply", "result": r})
            except Exception as e:
                self.push({"type": "chat", "from": a.id, "to": "You",
                           "text": f"(couldn't reply: {e})", "human": False})

    def push(self, event: dict):
        e = dict(event)
        if e.get("type") == "step":
            e["result"] = to_jsonable(e["result"])
        with self._lock:
            self._history.append(json.dumps(e))

    def wait(self):
        while True:
            time.sleep(1)


def start(port, agents, chat, ideas, digests) -> Dashboard:
    return Dashboard(port, agents, chat, ideas, digests)
