import { useState, useEffect, useRef, useCallback } from "react";

// ── Fonts ──────────────────────────────────────────────────────────────────
const fontLink = document.createElement("link");
fontLink.rel = "stylesheet";
fontLink.href =
  "https://fonts.googleapis.com/css2?family=Special+Elite&family=Oswald:wght@300;400;700&family=IM+Fell+English:ital@0;1&display=swap";
document.head.appendChild(fontLink);

// ── Constants ──────────────────────────────────────────────────────────────
const SCENE_COUNT = 8;
const SLIDE_DURATION = 5000; // ms per scene in auto-play

const NOIR_STYLE_SUFFIX =
  "noir comic book style, dramatic high-contrast black and white with deep shadows and stark highlights, ink hatching, gritty urban atmosphere, cinematic composition, 1940s detective pulp fiction aesthetic, heavy shadow bokeh, rain-slicked streets, dramatic chiaroscuro lighting";

// ── Claude API helpers ────────────────────────────────────────────────────
async function claudeJSON(systemPrompt, userMsg) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: systemPrompt,
      messages: [{ role: "user", content: userMsg }],
    }),
  });
  const data = await response.json();
  if (data.error) throw new Error(data.error.message);
  const raw = data.content.map((b) => b.text || "").join("");
  const clean = raw.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

// Step 1: get title + tagline + one-line plot per scene
async function generateOutline(userIdea) {
  const sys = `You are a noir story director. Given an idea, create a noir comic outline.
Respond ONLY with compact JSON, no markdown:
{"title":"short punchy title","tagline":"one noir tagline","beats":["beat1","beat2","beat3","beat4","beat5","beat6","beat7","beat8"]}
Each beat is ONE short sentence describing what happens in that scene. Be concise.`;
  return claudeJSON(sys, userIdea);
}

// Step 2: expand a single beat into a full scene object
async function generateScene(id, beat, title) {
  const sys = `You are a noir comic writer. Expand a scene beat into a scene object.
Respond ONLY with compact JSON, no markdown, no extra whitespace:
{"id":${id},"caption":"1 short noir narration sentence","dialogue":"one short line or empty string","imagePrompt":"visual scene description under 40 words, no text in image"}`;
  return claudeJSON(sys, `Story: "${title}". Scene ${id} beat: ${beat}`);
}

async function generateStoryWithClaude(userIdea, onSceneReady) {
  // 1. Get the outline (small response, safe)
  const outline = await generateOutline(userIdea);
  const story = { title: outline.title, tagline: outline.tagline, scenes: [] };

  // 2. Generate each scene individually (each call is tiny)
  for (let i = 0; i < outline.beats.length; i++) {
    const scene = await generateScene(i + 1, outline.beats[i], outline.title);
    story.scenes.push(scene);
    onSceneReady(scene, i);
  }
  return story;
}

// ── DALL-E 3 API ───────────────────────────────────────────────────────────
async function generateImage(prompt, apiKey) {
  const fullPrompt = `${prompt}. ${NOIR_STYLE_SUFFIX}`;
  const response = await fetch("https://api.openai.com/v1/images/generations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: "dall-e-3",
      prompt: fullPrompt,
      n: 1,
      size: "1024x1024",
      quality: "standard",
    }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error?.message || "DALL-E error");
  }
  const data = await response.json();
  return data.data[0].url;
}

// ── Typewriter ─────────────────────────────────────────────────────────────
function Typewriter({ text, speed = 28, onDone }) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    if (!text) return;
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(iv);
        onDone?.();
      }
    }, speed);
    return () => clearInterval(iv);
  }, [text]);
  return <span>{displayed}</span>;
}

// ── Progress bar ───────────────────────────────────────────────────────────
function ProgressBar({ current, total, onSelect }) {
  return (
    <div style={{ display: "flex", gap: 4, padding: "0 24px 16px" }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          onClick={() => onSelect(i)}
          style={{
            flex: 1,
            height: 3,
            background: i <= current ? "#e8c97a" : "rgba(255,255,255,0.2)",
            cursor: "pointer",
            transition: "background 0.3s",
            borderRadius: 2,
          }}
        />
      ))}
    </div>
  );
}

// ── Scene card ─────────────────────────────────────────────────────────────
function SceneCard({ scene, isActive }) {
  const [typed, setTyped] = useState(false);

  useEffect(() => {
    setTyped(false);
  }, [scene.id]);

  if (!isActive) return null;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        animation: "fadeIn 0.6s ease",
      }}
    >
      {/* Image */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {scene.imageUrl ? (
          <img
            src={scene.imageUrl}
            alt={`Scene ${scene.id}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "contrast(1.15) brightness(0.85)",
            }}
          />
        ) : (
          <div
            style={{
              width: "100%",
              height: "100%",
              background: "repeating-linear-gradient(45deg,#0a0a0a,#0a0a0a 10px,#111 10px,#111 20px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#333",
              fontFamily: "'Special Elite', monospace",
              fontSize: 18,
            }}
          >
            {scene.loading ? "Generating scene…" : "Awaiting image…"}
          </div>
        )}

        {/* Vignette */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.85) 100%)",
            pointerEvents: "none",
          }}
        />

        {/* Scene number badge */}
        <div
          style={{
            position: "absolute",
            top: 14,
            left: 14,
            background: "#e8c97a",
            color: "#0a0a0a",
            fontFamily: "'Oswald', sans-serif",
            fontWeight: 700,
            fontSize: 11,
            letterSpacing: 3,
            padding: "3px 10px",
            textTransform: "uppercase",
          }}
        >
          Scene {scene.id}
        </div>

        {/* Dialogue bubble */}
        {scene.dialogue && (
          <div
            style={{
              position: "absolute",
              top: 14,
              right: 14,
              maxWidth: "42%",
              background: "white",
              border: "2.5px solid #111",
              borderRadius: "16px 16px 4px 16px",
              padding: "8px 12px",
              fontFamily: "'IM Fell English', serif",
              fontStyle: "italic",
              fontSize: 13,
              color: "#111",
              lineHeight: 1.4,
              boxShadow: "3px 3px 0 #111",
            }}
          >
            "{scene.dialogue}"
          </div>
        )}
      </div>

      {/* Caption bar */}
      <div
        style={{
          background: "rgba(0,0,0,0.95)",
          borderTop: "2px solid #e8c97a",
          padding: "14px 20px 16px",
          minHeight: 72,
        }}
      >
        <p
          style={{
            margin: 0,
            fontFamily: "'Special Elite', monospace",
            fontSize: 14,
            color: "#d4d0c8",
            lineHeight: 1.65,
            letterSpacing: 0.3,
          }}
        >
          <Typewriter text={scene.caption} speed={22} />
        </p>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────
export default function NoirComicApp() {
  const [apiKey, setApiKey] = useState("");
  const [storyIdea, setStoryIdea] = useState("");
  const [phase, setPhase] = useState("input"); // input | generating | playing
  const [story, setStory] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState("");
  const [genStatus, setGenStatus] = useState("");
  const intervalRef = useRef(null);

  // Auto-advance
  useEffect(() => {
    if (!isPlaying || scenes.length === 0) return;
    intervalRef.current = setInterval(() => {
      setCurrentScene((prev) => {
        if (prev >= scenes.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, SLIDE_DURATION);
    return () => clearInterval(intervalRef.current);
  }, [isPlaying, scenes.length]);

  const handleGenerate = useCallback(async () => {
    if (!apiKey.trim()) return setError("Enter your OpenAI API key.");
    if (!storyIdea.trim()) return setError("Enter a story idea.");
    setError("");
    setPhase("generating");
    setGenStatus("Writing the story…");

    try {
      // 1. Generate outline (title + tagline + beats)
      setGenStatus("Writing story outline…");

      // 2. Generate scenes one-by-one; each call is tiny so it fits in 1000 tokens
      //    onSceneReady fires after each scene text is done — we immediately kick off its image
      const imageJobs = []; // track parallel image fetches

      const storyData = await generateStoryWithClaude(storyIdea, (scene, idx) => {
        // Add scene text immediately
        setScenes((prev) => {
          const next = [...prev];
          next[idx] = { ...scene, loading: true, imageUrl: null };
          return next;
        });
        setGenStatus(`Scene ${idx + 1} / ${SCENE_COUNT} written — painting panel…`);

        // Kick off DALL-E for this scene in parallel
        const job = generateImage(scene.imagePrompt, apiKey)
          .then((url) => {
            setScenes((prev) =>
              prev.map((s, i) => (i === idx ? { ...s, imageUrl: url, loading: false } : s))
            );
          })
          .catch(() => {
            setScenes((prev) =>
              prev.map((s, i) => (i === idx ? { ...s, loading: false } : s))
            );
          });
        imageJobs.push(job);
      });

      setStory(storyData);
      setPhase("playing");
      setCurrentScene(0);
      setIsPlaying(true);

      // Images continue loading in background after playback starts
      await Promise.allSettled(imageJobs);
    } catch (e) {
      setError("Error: " + e.message);
      setPhase("input");
    }
  }, [apiKey, storyIdea]);

  // ── Input screen ──────────────────────────────────────────────────────
  if (phase === "input") {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#080808",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          fontFamily: "'Oswald', sans-serif",
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(255,255,255,0.03) 39px, rgba(255,255,255,0.03) 40px)",
        }}
      >
        <div style={{ maxWidth: 520, width: "100%" }}>
          {/* Title */}
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <div
              style={{
                fontFamily: "'Special Elite', monospace",
                fontSize: 11,
                letterSpacing: 6,
                color: "#e8c97a",
                textTransform: "uppercase",
                marginBottom: 10,
              }}
            >
              ◆ Noir Comic Engine ◆
            </div>
            <h1
              style={{
                margin: 0,
                fontSize: 52,
                fontWeight: 700,
                color: "#f0ece0",
                letterSpacing: -1,
                textTransform: "uppercase",
                lineHeight: 1,
              }}
            >
              Dark
              <br />
              <span style={{ color: "#e8c97a" }}>Stories</span>
            </h1>
            <p
              style={{
                marginTop: 14,
                fontFamily: "'IM Fell English', serif",
                fontStyle: "italic",
                color: "#6b6860",
                fontSize: 15,
              }}
            >
              Every city has a shadow. Yours begins here.
            </p>
          </div>

          {/* Form */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 11,
                  letterSpacing: 3,
                  color: "#e8c97a",
                  marginBottom: 7,
                  textTransform: "uppercase",
                }}
              >
                OpenAI API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                style={{
                  width: "100%",
                  background: "#111",
                  border: "1px solid #2a2a2a",
                  borderBottom: "2px solid #e8c97a",
                  color: "#f0ece0",
                  padding: "12px 14px",
                  fontSize: 14,
                  fontFamily: "monospace",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 11,
                  letterSpacing: 3,
                  color: "#e8c97a",
                  marginBottom: 7,
                  textTransform: "uppercase",
                }}
              >
                Your Story Idea
              </label>
              <textarea
                value={storyIdea}
                onChange={(e) => setStoryIdea(e.target.value)}
                placeholder="A private detective in 1940s Los Angeles receives a mysterious envelope containing a photograph of his own funeral..."
                rows={4}
                style={{
                  width: "100%",
                  background: "#111",
                  border: "1px solid #2a2a2a",
                  borderBottom: "2px solid #e8c97a",
                  color: "#f0ece0",
                  padding: "12px 14px",
                  fontSize: 14,
                  fontFamily: "'IM Fell English', serif",
                  fontStyle: "italic",
                  outline: "none",
                  resize: "vertical",
                  lineHeight: 1.6,
                  boxSizing: "border-box",
                }}
              />
            </div>

            {error && (
              <p style={{ color: "#c0392b", fontFamily: "monospace", fontSize: 13, margin: 0 }}>
                ⚠ {error}
              </p>
            )}

            <button
              onClick={handleGenerate}
              style={{
                background: "#e8c97a",
                color: "#080808",
                border: "none",
                padding: "15px 0",
                fontSize: 14,
                fontFamily: "'Oswald', sans-serif",
                fontWeight: 700,
                letterSpacing: 4,
                textTransform: "uppercase",
                cursor: "pointer",
                marginTop: 8,
                transition: "opacity 0.2s",
              }}
              onMouseOver={(e) => (e.target.style.opacity = 0.85)}
              onMouseOut={(e) => (e.target.style.opacity = 1)}
            >
              Generate Comic
            </button>
          </div>
        </div>

        <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }`}</style>
      </div>
    );
  }

  // ── Generating screen ─────────────────────────────────────────────────
  if (phase === "generating") {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#080808",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 28,
          fontFamily: "'Oswald', sans-serif",
        }}
      >
        {/* Film strip loader */}
        <div style={{ display: "flex", gap: 6 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              style={{
                width: 18,
                height: 24,
                background: scenes[i]?.imageUrl
                  ? "#e8c97a"
                  : scenes[i]
                  ? "#3a3020"
                  : "#1a1a1a",
                border: "1px solid #333",
                borderRadius: 2,
                transition: "background 0.5s",
                animation: scenes[i]?.loading ? `pulse 1s ${i * 0.12}s infinite` : "none",
              }}
            />
          ))}
        </div>

        <div style={{ textAlign: "center" }}>
          <p
            style={{
              fontFamily: "'Special Elite', monospace",
              color: "#e8c97a",
              fontSize: 13,
              letterSpacing: 2,
              margin: 0,
            }}
          >
            {genStatus}
          </p>
          {story && (
            <p
              style={{
                fontFamily: "'IM Fell English', serif",
                fontStyle: "italic",
                color: "#6b6860",
                fontSize: 14,
                marginTop: 10,
              }}
            >
              "{story.title}"
            </p>
          )}
        </div>

        <style>{`@keyframes pulse { 0%,100%{opacity:.3} 50%{opacity:1} }`}</style>
      </div>
    );
  }

  // ── Playing screen ────────────────────────────────────────────────────
  const scene = scenes[currentScene];

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#050505",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px 16px",
        fontFamily: "'Oswald', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          marginBottom: 10,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 10,
              letterSpacing: 4,
              color: "#e8c97a",
              textTransform: "uppercase",
            }}
          >
            ◆ Now Playing
          </div>
          <div
            style={{
              fontFamily: "'Special Elite', monospace",
              color: "#f0ece0",
              fontSize: 17,
              marginTop: 2,
            }}
          >
            {story?.title}
          </div>
        </div>
        <div
          style={{
            fontFamily: "'IM Fell English', serif",
            fontStyle: "italic",
            color: "#4a4740",
            fontSize: 12,
            textAlign: "right",
            maxWidth: 180,
          }}
        >
          {story?.tagline}
        </div>
      </div>

      {/* Comic panel */}
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          aspectRatio: "1 / 1.15",
          background: "#0a0a0a",
          border: "2px solid #1c1c1c",
          position: "relative",
          overflow: "hidden",
          boxShadow: "0 0 60px rgba(0,0,0,0.9), inset 0 0 0 1px #222",
        }}
      >
        {scene && <SceneCard scene={scene} isActive key={scene.id} />}
      </div>

      {/* Progress + Controls */}
      <div style={{ width: "100%", maxWidth: 520, marginTop: 14 }}>
        <ProgressBar current={currentScene} total={scenes.length} onSelect={setCurrentScene} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16 }}>
          <button
            onClick={() => setCurrentScene((p) => Math.max(0, p - 1))}
            style={ctrlBtn}
          >
            ◀
          </button>

          <button
            onClick={() => setIsPlaying((p) => !p)}
            style={{ ...ctrlBtn, background: "#e8c97a", color: "#080808", width: 52, height: 52, fontSize: 18 }}
          >
            {isPlaying ? "⏸" : "▶"}
          </button>

          <button
            onClick={() => setCurrentScene((p) => Math.min(scenes.length - 1, p + 1))}
            style={ctrlBtn}
          >
            ▶
          </button>

          <button
            onClick={() => { setPhase("input"); setIsPlaying(false); setStory(null); setScenes([]); }}
            style={{ ...ctrlBtn, marginLeft: 12, fontSize: 11, letterSpacing: 2, width: "auto", padding: "0 14px" }}
          >
            NEW
          </button>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
      `}</style>
    </div>
  );
}

const ctrlBtn = {
  background: "#111",
  border: "1px solid #2a2a2a",
  color: "#e8c97a",
  width: 42,
  height: 42,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  fontFamily: "'Oswald', sans-serif",
  fontSize: 16,
  letterSpacing: 1,
  transition: "border-color 0.2s",
};
