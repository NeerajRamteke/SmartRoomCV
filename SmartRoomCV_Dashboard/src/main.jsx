import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, AirVent, AlertCircle, BarChart3, Camera, CheckCircle2, CircleHelp,
  Cpu, Fan, GraduationCap, Grid2X2, History, Lightbulb, Monitor, Power,
  Radio, RefreshCw, Settings, ShieldCheck, Users, Wifi, Zap
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";
const initialState = {
  total_people: 0, active_zones: 0,
  zones: {
    "1": { people: 0, light: false, fan: false },
    "2": { people: 0, light: false, fan: false },
    "3": { people: 0, light: false, fan: false },
    "4": { people: 0, light: false, fan: false }
  },
  tracks: [],
  system: { camera: "Waiting", yolo: "Waiting", bytetrack: "Waiting", blynk: "Not checked", raspberry_pi: "Not configured" },
  history: []
};
const zoneColors = ["green", "blue", "amber", "purple"];
const demoHistory = Array.from({ length: 12 }, (_, i) => ({
  time: `${String(10 + Math.floor(i / 6)).padStart(2, "0")}:${String((i * 5) % 60).padStart(2, "0")}`,
  people: [4, 5, 4, 7, 8, 6, 9, 7, 5, 6, 4, 0][i]
}));

function StatusDot({ status }) {
  const s = String(status || "").toLowerCase();
  const ok = ["online", "running", "connected", "ok"].some(v => s.includes(v));
  const wait = ["waiting", "not configured", "not checked"].some(v => s.includes(v));
  return <span className={`dot ${ok ? "ok" : wait ? "wait" : "bad"}`} />;
}

function App() {
  const [data, setData] = useState(initialState);
  const [apiOnline, setApiOnline] = useState(false);
  const [activeNav, setActiveNav] = useState("Overview");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    try {
      const res = await fetch(`${API}/api/state`, { cache: "no-store" });
      if (!res.ok) throw new Error("API unavailable");
      const next = await res.json();
      setData(prev => ({ ...prev, ...next }));
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  }
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 1500);
    return () => clearInterval(timer);
  }, []);

  const zones = data.zones || initialState.zones;
  const lightsOn = Object.values(zones).filter(z => z.light).length;
  const fansOn = Object.values(zones).filter(z => z.fan).length;
  const history = data.history?.length ? data.history : demoHistory;
  const tracksByZone = useMemo(() => {
    const map = { "1": [], "2": [], "3": [], "4": [] };
    (data.tracks || []).forEach(t => { if (map[String(t.zone)]) map[String(t.zone)].push(t); });
    return map;
  }, [data.tracks]);

  async function control(zone, device, value) {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zone, device, value })
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.error || "Control failed");
      setNotice(`Zone ${zone} ${device} set ${value ? "ON" : "OFF"} in dashboard state.`);
      await refresh();
    } catch {
      setNotice("Could not reach the backend. Start server.py and try again.");
    } finally {
      setLoading(false);
      setTimeout(() => setNotice(""), 4000);
    }
  }

  async function allControls(device, value) {
    for (const zone of ["1", "2", "3", "4"]) await control(zone, device, value);
  }

  const navItems = [
    ["Overview", Grid2X2], ["Zones", Monitor], ["Devices", Cpu],
    ["People", Users], ["Analytics", BarChart3], ["History", History], ["Settings", Settings]
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><GraduationCap size={29}/></div><div><strong>SmartRoom<span>CV</span></strong><small>SMART CLASSROOM</small></div></div>
        <div className="nav-label">WORKSPACE</div>
        <nav>{navItems.map(([label, Icon]) => <button key={label} className={`nav-item ${activeNav === label ? "selected" : ""}`} onClick={() => setActiveNav(label)}><Icon size={18}/><span>{label}</span>{label === "Zones" && <b>4</b>}</button>)}</nav>
        <div className="side-bottom">
          <div className="system-title"><span className="pulse"></span> SYSTEM STATUS</div>
          {[["Dashboard API", apiOnline ? "Online" : "Offline"], ["Camera", data.system?.camera], ["YOLO11", data.system?.yolo], ["ByteTrack", data.system?.bytetrack], ["Blynk", data.system?.blynk], ["Raspberry Pi", data.system?.raspberry_pi]].map(([label, value]) =>
            <div className="system-row" key={label}><span>{label}</span><span className="system-value"><StatusDot status={value}/>{value || "Unknown"}</span></div>
          )}
        </div>
        <div className="sidebar-footer">SmartRoomCV <span>v1.0</span></div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><div className="eyebrow"><span className="pulse"></span> AI-POWERED OCCUPANCY AUTOMATION</div><h1>{activeNav === "Overview" ? "Classroom Overview" : activeNav}</h1><p>Monitor people, zones and smart devices in real time.</p></div>
          <div className="top-actions"><div className={`connection ${apiOnline ? "connected" : ""}`}><StatusDot status={apiOnline ? "Online" : "Offline"}/>{apiOnline ? "API Connected" : "API Offline"}</div><button className="icon-btn" onClick={refresh} title="Refresh"><RefreshCw size={17}/></button><div className="avatar">SC</div></div>
        </header>

        {notice && <div className="notice"><AlertCircle size={16}/>{notice}</div>}

        <section className="metrics">
          <Metric title="Total people" value={data.total_people ?? 0} sub="Tracked in current frame" icon={Users} tone="blue"/>
          <Metric title="Active zones" value={`${data.active_zones ?? 0}`} suffix="/ 4" sub="Zones currently occupied" icon={Grid2X2} tone="green"/>
          <Metric title="Lights ON" value={lightsOn} suffix="/ 4" sub="Zone lighting status" icon={Lightbulb} tone="amber"/>
          <Metric title="Fans ON" value={fansOn} suffix="/ 4" sub="Zone ventilation status" icon={Fan} tone="purple"/>
        </section>

        <section className="primary-grid">
          <div className="panel camera-panel">
            <div className="panel-heading"><div><span className="live-dot"></span><h2>Zone monitoring</h2><p>Quadrant view · YOLO11 + ByteTrack</p></div><span className="pill"><Camera size={13}/> LIVE DATA</span></div>
            <div className="camera-view">
              <div className="camera-placeholder">
                <Camera size={36}/><strong>Camera feed preview</strong><span>Connect your Python camera stream to display live video here.</span>
              </div>
              <div className="quadrant-grid">
                {[1,2,3,4].map(n => <div className={`quadrant q${n}`} key={n}><span className="zone-tag">ZONE {n}</span>{(tracksByZone[String(n)] || []).map((t, i) => <div key={`${t.id}-${i}`} className="track-box" style={{left: `${Math.max(2,Math.min(80,(t.x || .5)*100-8))}%`,top:`${Math.max(12,Math.min(75,(t.y || .5)*100-12))}%`}}>ID: {t.id}</div>)}</div>)}
              </div>
              <div className="camera-overlay"><span><span className="live-dot"></span> CAMERA 01</span><span>4-ZONE GRID</span></div>
            </div>
            <div className="camera-foot"><span><StatusDot status={data.system?.camera}/>{data.system?.camera || "Camera waiting"}</span><span><Radio size={13}/> Tracking IDs: {data.tracks?.length || 0}</span><span>Zones: 4</span></div>
          </div>

          <div className="panel zone-panel">
            <div className="panel-heading"><div><h2>Zone status</h2><p>Occupancy and device states</p></div><button className="text-btn" onClick={() => setActiveNav("Zones")}>View all ↗</button></div>
            <div className="zone-grid">
              {[1,2,3,4].map((n) => {
                const z = zones[String(n)] || {};
                return <div className={`zone-card ${zoneColors[n-1]}`} key={n}>
                  <div className="zone-card-head"><span>ZONE 0{n}</span><span className={`occupancy ${Number(z.people)>0 ? "occupied" : ""}`}>{Number(z.people)>0 ? "OCCUPIED" : "VACANT"}</span></div>
                  <div className="zone-people"><strong>{z.people ?? 0}</strong><span>people detected</span><Users size={23}/></div>
                  <div className="device-buttons">
                    <button disabled={loading} onClick={() => control(String(n),"light",!z.light)} className={z.light ? "is-on" : ""}><Lightbulb size={15}/><span>Light</span><b>{z.light ? "ON" : "OFF"}</b></button>
                    <button disabled={loading} onClick={() => control(String(n),"fan",!z.fan)} className={z.fan ? "is-on" : ""}><Fan size={15}/><span>Fan</span><b>{z.fan ? "ON" : "OFF"}</b></button>
                  </div>
                </div>;
              })}
            </div>
            <div className="zone-note"><ShieldCheck size={15}/> Device states update from the API. Controls here change dashboard state only until GPIO/Blynk control is connected.</div>
          </div>
        </section>

        <section className="lower-grid">
          <div className="panel chart-panel">
            <div className="panel-heading"><div><h2>Occupancy analytics</h2><p>Recent people-count samples</p></div><span className="pill">LIVE / API</span></div>
            <div className="chart-legend"><span><i></i> People detected</span><span className="muted">Last {history.length} samples</span></div>
            <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history} margin={{top:8,right:8,left:-22,bottom:0}}><defs><linearGradient id="peopleFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#35d39a" stopOpacity={0.25}/><stop offset="95%" stopColor="#35d39a" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#1d2d40" strokeDasharray="3 4" vertical={false}/><XAxis dataKey="time" tick={{fill:"#7f91a8",fontSize:10}} axisLine={false} tickLine={false}/><YAxis allowDecimals={false} tick={{fill:"#7f91a8",fontSize:10}} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:"#101d2c",border:"1px solid #263a50",borderRadius:10,color:"#f3f7fb"}}/><Area type="monotone" dataKey="people" stroke="#35d39a" strokeWidth={2.5} fill="url(#peopleFill)" activeDot={{r:4,fill:"#35d39a"}}/></AreaChart></ResponsiveContainer></div>
          </div>

          <div className="panel devices-panel">
            <div className="panel-heading"><div><h2>System components</h2><p>Integration health</p></div><Activity size={18} className="heading-icon"/></div>
            {[
              ["Camera input", Camera, data.system?.camera],
              ["YOLO11 detector", Cpu, data.system?.yolo],
              ["ByteTrack tracker", Activity, data.system?.bytetrack],
              ["Blynk Cloud", Wifi, data.system?.blynk],
              ["Raspberry Pi", Zap, data.system?.raspberry_pi]
            ].map(([label, Icon, status]) => <div className="component-row" key={label}><div className="component-icon"><Icon size={16}/></div><span>{label}</span><div className="component-status"><StatusDot status={status}/>{status || "Unknown"}</div></div>)}
            <div className="integration-tip"><CircleHelp size={15}/><span>Run <code>server.py</code> and POST real detection state to activate live updates.</span></div>
          </div>

          <div className="panel quick-panel">
            <div className="panel-heading"><div><h2>Quick controls</h2><p>Bulk device commands</p></div><Power size={18} className="heading-icon"/></div>
            <button className="bulk-btn light-on" disabled={loading} onClick={() => allControls("light",true)}><Lightbulb size={19}/><span><b>All lights ON</b><small>Enable lighting in all zones</small></span></button>
            <button className="bulk-btn light-off" disabled={loading} onClick={() => allControls("light",false)}><Lightbulb size={19}/><span><b>All lights OFF</b><small>Disable lighting in all zones</small></span></button>
            <button className="bulk-btn fan-on" disabled={loading} onClick={() => allControls("fan",true)}><Fan size={19}/><span><b>All fans ON</b><small>Enable fans in all zones</small></span></button>
            <button className="bulk-btn fan-off" disabled={loading} onClick={() => allControls("fan",false)}><Fan size={19}/><span><b>All fans OFF</b><small>Disable fans in all zones</small></span></button>
          </div>
        </section>
        <EnergyPredictionPanel API={API} zones={zones} />

        <footer className="footer"><div><GraduationCap size={17}/> <b>SmartRoomCV</b><span>AI-based smart classroom automation</span></div><div>OpenCV <i/> YOLO11 <i/> ByteTrack <i/> Raspberry Pi <i/> Blynk IoT</div></footer>
      </main>
    </div>
  );
}

function Metric({title,value,suffix,sub,icon:Icon,tone}) {
  return <div className={`metric-card ${tone}`}><div className="metric-icon"><Icon size={21}/></div><div className="metric-copy"><span>{title}</span><div className="metric-value">{value}<small>{suffix}</small></div><p>{sub}</p></div><div className="metric-accent"></div></div>;
}

function EnergyPredictionPanel({ API, zones }) {
  const [duration, setDuration] = useState("60");
  const [result, setResult] = useState(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [error, setError] = useState("");

  const zoneSignature = [1, 2, 3, 4].map((zoneNumber) => {
    const zone = zones[String(zoneNumber)] || {};
    return `${Number(zone.people || 0)}:${Boolean(zone.light)}:${Boolean(zone.fan)}`;
  }).join("|");
  const totalPeople = [1, 2, 3, 4].reduce(
    (total, zoneNumber) => total + Number(zones[String(zoneNumber)]?.people || 0),
    0
  );
  const occupiedZones = [1, 2, 3, 4].filter(
    (zoneNumber) => Number(zones[String(zoneNumber)]?.people || 0) > 0
  ).length;

  async function predictEnergy(signal) {
    setLoadingPrediction(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/predict-lab-energy?interval_seconds=${duration}`,
        { cache: "no-store", signal }
      );

      const prediction = await response.json();

      if (!response.ok) {
        throw new Error(prediction.error || "Prediction request failed.");
      }

      setResult(prediction);
    } catch (err) {
      if (err.name === "AbortError") return;
      setError(err.message || "Could not connect to the energy prediction API.");
    } finally {
      if (!signal?.aborted) setLoadingPrediction(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    predictEnergy(controller.signal);
    return () => controller.abort();
  }, [API, duration, zoneSignature]);

  return (
    <section className="energy-prediction panel">
      <div className="panel-heading">
        <div>
          <h2>Whole-Lab Energy Prediction</h2>
          <p>Random Forest predictions from live counts and device states in all four zones.</p>
        </div>
        <span className="pill">LIVE ML MODEL</span>
      </div>

      <div className="energy-input-grid">
        <label>
          Prediction duration
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          >
            <option value="60">1 minute</option>
            <option value="120">2 minutes</option>
            <option value="300">5 minutes</option>
            <option value="600">10 minutes</option>
            <option value="1800">30 minutes</option>
            <option value="3600">1 hour</option>
          </select>
        </label>

        <div className="energy-current-state">
          <span>People across all zones</span>
          <strong>{totalPeople}</strong>
        </div>

        <div className="energy-current-state">
          <span>Occupied zones</span>
          <strong>{occupiedZones} / 4</strong>
        </div>

        <div className="energy-current-state">
          <span>Prediction window</span>
          <strong>{Number(duration) / 60} min</strong>
        </div>
      </div>

      <button
        className="energy-predict-button"
        onClick={() => predictEnergy()}
        disabled={loadingPrediction}
      >
        <RefreshCw size={17} />
        {loadingPrediction ? "Updating prediction..." : "Refresh prediction"}
      </button>

      {error && (
        <div className="energy-error" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className="energy-result">
          <div className="energy-result-main">
            <span>Predicted energy for all four zones</span>
            <strong>
              {Number(result.total_predicted_energy_Wh).toFixed(4)}
              <small> Wh</small>
            </strong>
            <span>
              {result.total_people} people · {result.interval_seconds} seconds · Updated {new Date(result.timestamp).toLocaleTimeString()}
            </span>
          </div>

          <div className="energy-result-details">
            <div>
              <span>Total estimated device power</span>
              <strong>{result.total_estimated_power_W} W</strong>
            </div>
            <div>
              <span>Formula-based lab estimate</span>
              <strong>{result.total_formula_energy_Wh} Wh</strong>
            </div>
          </div>

          <div className="energy-zone-results">
            {(result.zones || []).map((zoneResult) => (
              <div className="energy-zone-result" key={zoneResult.zone}>
                <strong>Zone 0{zoneResult.zone}</strong>
                <span>{zoneResult.people} people</span>
                <b>{Number(zoneResult.predicted_energy_Wh).toFixed(4)} Wh</b>
                <small>{zoneResult.estimated_power_W} W · Light {zoneResult.light_on ? "ON" : "OFF"} · Fan {zoneResult.fan_on ? "ON" : "OFF"}</small>
              </div>
            ))}
          </div>

          <p className="energy-disclaimer">
            Simulated estimate using assumed device wattages; this is a model prediction, not a physical energy measurement.
          </p>
        </div>
      )}
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
