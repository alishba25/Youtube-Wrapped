// ---------- Cycling hero word ----------
const CYCLE_WORDS = ["decoded.", "The Night Owl.", "The Tutorial Hoarder.", "The Sound Chaser.", "decoded."];
let cycleIndex = 0;
const cycleEl = document.getElementById("cycling-word");

if (cycleEl) {
  setInterval(() => {
    cycleIndex = (cycleIndex + 1) % CYCLE_WORDS.length;
    cycleEl.style.opacity = 0;
    setTimeout(() => {
      cycleEl.textContent = CYCLE_WORDS[cycleIndex];
      cycleEl.style.opacity = 1;
    }, 250);
  }, 2600);
}

// ---------- Persona teaser marquee ----------
const PERSONA_TEASERS = [
  { emoji: "🔦", name: "The 3AM Documentary Detective" },
  { emoji: "🎮", name: "The Gaming Grinder" },
  { emoji: "🎧", name: "The Sound Chaser" },
  { emoji: "🛠️", name: "The Tutorial Hoarder" },
  { emoji: "📰", name: "The News Junkie" },
  { emoji: "🐾", name: "The Softie" },
  { emoji: "🧳", name: "The Wanderer" },
  { emoji: "🏟️", name: "The Sports Fanatic" },
];

const track = document.getElementById("persona-track");
if (track) {
  const chips = [...PERSONA_TEASERS, ...PERSONA_TEASERS] // duplicated for seamless loop
    .map((p) => `<span class="persona-chip">${p.emoji} ${p.name}</span>`)
    .join("");
  track.innerHTML = chips;
}

// ---------- Section helpers ----------
const sections = {
  paths: document.getElementById("paths-section"),
  howto: document.getElementById("howto-panel"),
  status: document.getElementById("status-panel"),
  results: document.getElementById("results-section"),
  error: document.getElementById("error-panel"),
};

function show(name) {
  Object.entries(sections).forEach(([key, el]) => {
    if (!el) return;
    el.hidden = key !== name;
  });
}

function showStatus(text) {
  document.getElementById("status-text").textContent = text;
  show("status");
}

function showError(message) {
  document.getElementById("error-text").textContent = message;
  show("error");
}

// ---------- How-to panel ----------
document.getElementById("takeout-howto-btn")?.addEventListener("click", () => {
  sections.howto.hidden = false;
  sections.howto.scrollIntoView({ behavior: "smooth", block: "center" });
});
document.getElementById("howto-close")?.addEventListener("click", () => {
  sections.howto.hidden = true;
});

// ---------- Takeout upload ----------
document.getElementById("takeout-file-input")?.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  showStatus("Reading your watch history and matching it up with YouTube's category data — this can take a minute for a large export.");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch("/api/takeout/wrapped", { method: "POST", body: formData });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Something went wrong processing that file.");
    }
    const result = await resp.json();
    startStory(result);
  } catch (err) {
    showError(err.message);
  }
});

// ---------- Auto-run Taste / Creator after OAuth redirect ----------
async function runOAuthPath(pathType) {
  showStatus(
    pathType === "creator"
      ? "Pulling your channel's last 90 days of analytics…"
      : "Looking through your liked videos and subscriptions…"
  );

  try {
    const resp = await fetch(`/api/${pathType}/wrapped`, { method: "POST" });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || "Something went wrong generating your wrapped.");
    }
    const result = await resp.json();
    startStory(result);
  } catch (err) {
    showError(err.message);
  }
}

// ================= Story reveal engine =================

const ACCENT_BY_PATH = { takeout: "var(--takeout)", taste: "var(--taste)", creator: "var(--creator)" };
const PATH_LABEL = { takeout: "Takeout", taste: "Taste", creator: "Creator" };

let currentResult = null;
let slides = [];
let slideIndex = 0;

function buildSlides(result) {
  const list = [];

  list.push({ kind: "intro", pathLabel: PATH_LABEL[result.path_type] || "YouTube" });
  list.push({ kind: "persona", emoji: result.persona_emoji, title: result.persona_name });

  if (result.roast_line) {
    list.push({ kind: "roast", line: result.roast_line });
  }

  list.push({ kind: "headline", text: result.headline_stat });

  if (result.top_categories.length) {
    list.push({ kind: "list", heading: "Top categories", items: result.top_categories.map((c) => c[0]) });
  }

  if (result.top_channels.length) {
    list.push({ kind: "list", heading: "Top channels", items: result.top_channels.map((c) => c[0]) });
  }

  const facts = [...result.extra_facts];
  if (result.peak_hour_label) facts.push(`Peak watching hour: ${result.peak_hour_label}`);
  if (facts.length) {
    list.push({ kind: "facts", items: facts });
  }

  list.push({
    kind: "outro",
    emoji: result.persona_emoji,
    title: result.persona_name,
    tagline: result.persona_tagline,
  });

  return list;
}

function renderSlideContent(slide) {
  switch (slide.kind) {
    case "intro":
      return `
        <div class="slide-content">
          <p class="slide-eyebrow">${slide.pathLabel} wrapped</p>
          <h2 class="slide-title">Your wrapped is ready.</h2>
        </div>`;

    case "persona":
      return `
        <div class="slide-content">
          <p class="slide-eyebrow">You are...</p>
          <div class="slide-emoji">${slide.emoji}</div>
          <h2 class="slide-title">${slide.title}</h2>
        </div>`;

    case "roast":
      return `
        <div class="slide-content">
          <p class="slide-eyebrow">Real talk</p>
          <p class="slide-roast">${slide.line}</p>
        </div>`;

    case "headline":
      return `
        <div class="slide-content">
          <p class="slide-eyebrow">The number</p>
          <p class="slide-stat">${slide.text}</p>
        </div>`;

    case "list":
      return `
        <div class="slide-content">
          <p class="slide-list-heading">${slide.heading}</p>
          <ol class="slide-list">
            ${slide.items
              .map(
                (item, i) =>
                  `<li style="animation-delay:${i * 90}ms"><span class="rank">${i + 1}</span>${item}</li>`
              )
              .join("")}
          </ol>
        </div>`;

    case "facts":
      return `
        <div class="slide-content">
          <p class="slide-list-heading">Extra facts</p>
          <ul class="slide-facts">
            ${slide.items.map((f) => `<li>${f}</li>`).join("")}
          </ul>
        </div>`;

    case "outro":
      return `
        <div class="slide-content">
          <div class="slide-emoji">${slide.emoji}</div>
          <h2 class="slide-title">${slide.title}</h2>
          <p class="slide-roast">${slide.tagline}</p>
          <div class="slide-outro-actions">
            <button class="primary-btn" id="download-card-btn">Download shareable card</button>
            <button class="link-btn" id="start-over-btn">Start over</button>
          </div>
        </div>`;

    default:
      return "";
  }
}

function renderProgress() {
  const bar = document.getElementById("story-progress");
  bar.innerHTML = slides
    .map((_, i) => {
      const state = i < slideIndex ? "is-past" : i === slideIndex ? "is-current" : "";
      return `<div class="story-progress-seg ${state}"><div class="story-progress-fill"></div></div>`;
    })
    .join("");
}

function renderSlide() {
  const slideEl = document.getElementById("story-slide");
  slideEl.innerHTML = renderSlideContent(slides[slideIndex]);
  renderProgress();

  const hint = document.getElementById("story-hint");
  const isLast = slideIndex === slides.length - 1;
  hint.style.display = isLast ? "none" : "block";

  // The invisible tap-to-advance zones sit above the slide content (higher
  // z-index, so taps anywhere register as "next"/"prev"). On every other
  // slide that's fine since there's nothing else to click there - but on
  // the last slide the Download/Start over buttons live in that same space,
  // and the tap zones were silently swallowing clicks meant for them.
  // Disabling the zones here lets clicks reach the real buttons; going back
  // still works via keyboard arrows or swipe, both bound to the viewport
  // itself rather than these overlay divs.
  const tapPrev = document.getElementById("story-tap-prev");
  const tapNext = document.getElementById("story-tap-next");
  if (tapPrev) tapPrev.style.pointerEvents = isLast ? "none" : "";
  if (tapNext) tapNext.style.pointerEvents = isLast ? "none" : "";

  if (isLast) {
    document.getElementById("download-card-btn")?.addEventListener("click", handleDownloadCard);
    document.getElementById("start-over-btn")?.addEventListener("click", () => {
      window.location.href = "/";
    });
  }
}

function goTo(index) {
  slideIndex = Math.max(0, Math.min(slides.length - 1, index));
  renderSlide();
}

function startStory(result) {
  currentResult = result;
  slides = buildSlides(result);
  slideIndex = 0;

  sections.results.style.setProperty("--accent", ACCENT_BY_PATH[result.path_type] || "var(--taste)");

  show("results");
  renderSlide();
  sections.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("story-tap-prev")?.addEventListener("click", () => goTo(slideIndex - 1));
document.getElementById("story-tap-next")?.addEventListener("click", () => goTo(slideIndex + 1));

document.addEventListener("keydown", (e) => {
  if (sections.results.hidden) return;
  if (e.key === "ArrowRight") goTo(slideIndex + 1);
  if (e.key === "ArrowLeft") goTo(slideIndex - 1);
});

// Basic swipe support for mobile
let touchStartX = null;
const viewport = document.querySelector(".story-viewport");
viewport?.addEventListener("touchstart", (e) => {
  touchStartX = e.touches[0].clientX;
});
viewport?.addEventListener("touchend", (e) => {
  if (touchStartX === null) return;
  const delta = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(delta) > 40) {
    goTo(delta < 0 ? slideIndex + 1 : slideIndex - 1);
  }
  touchStartX = null;
});

// ---------- Download card ----------
async function handleDownloadCard() {
  if (!currentResult) return;
  const btn = document.getElementById("download-card-btn");
  const originalText = btn.textContent;
  btn.textContent = "Generating…";
  btn.disabled = true;

  try {
    const resp = await fetch("/api/card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentResult),
    });
    if (!resp.ok) throw new Error("Couldn't generate the card image.");

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "youtube-wrapped.png";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---------- Error dismiss ----------
document.getElementById("error-dismiss-btn")?.addEventListener("click", () => {
  window.location.href = "/";
});

// ---------- On load: check for OAuth redirect params ----------
(function init() {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");
  const path = params.get("path");
  const ready = params.get("ready");

  if (error) {
    const messages = {
      invalid_path: "That sign-in path isn't recognized.",
      state_mismatch: "Your sign-in session expired — please try again.",
      token_exchange_failed: "Google sign-in didn't complete — please try again.",
      access_denied: "Sign-in was cancelled.",
    };
    showError(messages[error] || "Something went wrong signing you in.");
    return;
  }

  if (ready && (path === "taste" || path === "creator")) {
    runOAuthPath(path);
  }
})();