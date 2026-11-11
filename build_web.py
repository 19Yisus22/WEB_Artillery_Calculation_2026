import shutil
import subprocess
import sys
import tempfile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "web_build"
MOBILE_ORIENTATION_UI = """
<style>
html,
body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  overscroll-behavior: none;
}
body {
  margin: 0;
  background: #070a18 !important;
}
#mobile-angle-input {
  position: fixed;
  z-index: 10500;
  display: none;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: transparent;
  caret-color: transparent;
  opacity: 0.01;
  font-size: 16px;
  touch-action: manipulation;
}
#canvas.emscripten {
  position: fixed !important;
  top: 50% !important;
  left: 50% !important;
  right: auto !important;
  bottom: auto !important;
  max-width: 100vw !important;
  max-height: 100vh !important;
  transform: translate(-50%, -50%);
  touch-action: none;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
#orientation-gate {
  position: fixed;
  inset: 0;
  z-index: 12000;
  display: none;
  place-items: center;
  padding: 24px;
  box-sizing: border-box;
  background: #070a18;
  color: #e9eeff;
  font: 15px/1.5 system-ui, sans-serif;
  text-align: center;
}
body.needs-landscape #orientation-gate {
  display: grid;
}
#orientation-gate .orientation-card {
  width: min(100%, 380px);
  padding: 28px 24px;
  border: 1px solid rgba(56, 224, 255, 0.28);
  border-radius: 18px;
  background: linear-gradient(155deg, #111d37, #080e1e);
  box-shadow: 0 20px 70px rgba(0, 0, 0, 0.48);
}
#orientation-gate .orientation-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  color: #38e0ff;
  animation: rotate-phone 1.8s ease-in-out infinite alternate;
}
#orientation-gate h2 {
  margin: 0 0 8px;
  font-size: 22px;
}
#orientation-gate p {
  margin: 8px 0;
  color: #aab6d9;
}
#orientation-status {
  min-height: 3em;
  font-size: 13px;
}
#orientation-gate button {
  width: 100%;
  min-height: 48px;
  margin-top: 8px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(100deg, #38e0ff, #76f0d0);
  color: #071321;
  font: 700 15px/1.2 system-ui, sans-serif;
  cursor: pointer;
  touch-action: manipulation;
}
#orientation-gate button:focus-visible {
  outline: 3px solid #ffb042;
  outline-offset: 3px;
}
@keyframes rotate-phone {
  to { transform: rotate(90deg); }
}
#game-loader {
  position: fixed;
  inset: 0;
  z-index: 11000;
  display: grid;
  place-items: center;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 45%, rgba(34, 86, 122, 0.24), transparent 56%),
    linear-gradient(145deg, #070a18, #0b132b 58%, #080b1b);
  color: #e9eeff;
  font: 14px/1.5 system-ui, sans-serif;
  text-align: center;
  transition: opacity 400ms ease, visibility 400ms ease;
}
#game-loader::before,
#game-loader::after {
  position: absolute;
  inset: 0;
  content: "";
  pointer-events: none;
}
#game-loader::before {
  background-image:
    linear-gradient(rgba(104, 143, 191, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(104, 143, 191, 0.055) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse, black, transparent 72%);
}
#game-loader::after {
  background: radial-gradient(circle, rgba(56, 224, 255, 0.65) 1px, transparent 1.5px);
  background-size: 34px 34px;
  mask-image: linear-gradient(transparent, black 35%, transparent);
  opacity: 0.18;
}
#game-loader .loader-card {
  position: relative;
  z-index: 1;
  width: min(100%, 520px);
  padding: 30px 34px 24px;
  overflow: hidden;
  border: 1px solid rgba(135, 168, 215, 0.2);
  border-radius: 20px;
  background: linear-gradient(155deg, rgba(17, 29, 55, 0.96), rgba(8, 14, 30, 0.97));
  box-shadow: 0 28px 90px rgba(0, 0, 0, 0.5), 0 0 48px rgba(56, 224, 255, 0.07);
  text-align: left;
}
#game-loader .loader-card::before {
  position: absolute;
  inset: 0 18% auto;
  height: 1px;
  content: "";
  background: linear-gradient(90deg, transparent, rgba(56, 224, 255, 0.75), transparent);
}
#game-loader .loader-header,
#game-loader .loader-brand,
#game-loader .loader-online {
  display: flex;
  align-items: center;
}
#game-loader .loader-header {
  justify-content: space-between;
  gap: 12px;
}
#game-loader .loader-brand {
  gap: 10px;
  color: #e9eeff;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
}
#game-loader .loader-mark {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid rgba(56, 224, 255, 0.38);
  border-radius: 8px;
  color: #38e0ff;
  font-size: 16px;
}
#game-loader .loader-online {
  gap: 7px;
  color: #91a1c4;
  font: 600 9px/1.4 ui-monospace, monospace;
  letter-spacing: 0.13em;
}
#game-loader .loader-online::before {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  content: "";
  background: #72e0a1;
  box-shadow: 0 0 10px rgba(114, 224, 161, 0.7);
}
#game-loader .loader-scene {
  display: block;
  width: 100%;
  height: auto;
  margin: 22px 0 18px;
  border: 1px solid rgba(115, 150, 195, 0.14);
  border-radius: 12px;
  background: radial-gradient(ellipse at 65% 80%, rgba(35, 83, 106, 0.25), transparent 60%),
    rgba(5, 11, 24, 0.75);
}
#game-loader .loader-kicker {
  margin: 0 0 5px;
  color: #ffb042;
  font: 700 9px/1.4 ui-monospace, monospace;
  letter-spacing: 0.18em;
}
#game-loader h1 {
  margin: 0;
  font-size: clamp(22px, 5vw, 28px);
  letter-spacing: 0.02em;
}
#game-loader .loader-copy {
  margin: 5px 0 18px;
  color: #aab6d9;
}
#game-loader .loader-track {
  height: 3px;
  overflow: hidden;
  border-radius: 4px;
  background: rgba(157, 177, 229, 0.15);
}
#game-loader .loader-track span {
  display: block;
  width: 0;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #38e0ff, #ffb042);
  box-shadow: 0 0 14px rgba(56, 224, 255, 0.7);
  transition: width 180ms ease-out;
}
#game-loader .loader-status {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
  color: #7483ad;
  font: 9px/1.5 ui-monospace, monospace;
  letter-spacing: 0.12em;
}
#game-loader #loader-progress-percent {
  min-width: 3.5em;
  color: #38e0ff;
  font-weight: 700;
  text-align: right;
}
body.game-ready #game-loader {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}
@media (max-width: 480px) {
  #game-loader {
    padding: 16px;
  }
  #game-loader .loader-card {
    padding: 22px 20px 18px;
    border-radius: 16px;
  }
  #game-loader .loader-scene {
    margin: 18px 0 15px;
  }
  #game-loader .loader-brand {
    font-size: 10px;
  }
  #game-loader .loader-online {
    font-size: 8px;
  }
}
@media (orientation: portrait) and (pointer: coarse) {
  #orientation-gate {
    display: grid;
  }
}
@media (max-height: 520px) {
  #game-loader {
    padding: 10px;
  }
  #game-loader .loader-card {
    width: min(100%, 460px);
    padding: 16px 24px 14px;
  }
  #game-loader .loader-scene {
    max-height: 110px;
    margin: 10px 0;
  }
  #game-loader .loader-copy {
    margin-bottom: 10px;
  }
}
@media (prefers-reduced-motion: reduce) {
  #game-loader .loader-track span {
    animation: none;
    width: 100%;
    transform: none;
  }
}
</style>
<div id="game-loader" role="status" aria-live="polite" aria-label="Cargando Artillery Calculation">
  <div class="loader-card">
    <div class="loader-header">
      <div class="loader-brand"><span class="loader-mark" aria-hidden="true">⌖</span> Artillery Calculation</div>
      <div class="loader-online">SISTEMA ACTIVO</div>
    </div>
    <svg class="loader-scene" viewBox="0 0 440 180" role="img" aria-label="Cañón calculando la trayectoria hacia el objetivo">
      <defs>
        <linearGradient id="trajectory" x1="0" x2="1">
          <stop offset="0" stop-color="#38e0ff" />
          <stop offset="1" stop-color="#ffb042" />
        </linearGradient>
        <radialGradient id="target-glow">
          <stop stop-color="#ffb042" stop-opacity=".24" />
          <stop offset="1" stop-color="#ffb042" stop-opacity="0" />
        </radialGradient>
      </defs>
      <path d="M0 148H440" stroke="#7186a4" stroke-opacity=".3" />
      <path d="M0 149l48-15 33 8 51-20 38 12 51-7 45 14 42-11 38 14 42-9 52 13v32H0z" fill="#12263a" fill-opacity=".72" />
      <path d="M25 148l45-14 23 5 52-17 37 10" fill="none" stroke="#38e0ff" stroke-opacity=".25" />
      <circle cx="367" cy="50" r="44" fill="url(#target-glow)" />
      <path d="M112 112Q236 9 367 50" fill="none" stroke="url(#trajectory)" stroke-dasharray="4 7" stroke-linecap="round" stroke-width="2" />
      <circle cx="244" cy="52" r="4" fill="#ffb042" />
      <circle cx="367" cy="50" r="17" fill="none" stroke="#ffb042" stroke-opacity=".8" />
      <circle cx="367" cy="50" r="6" fill="none" stroke="#ffb042" stroke-width="1.5" />
      <path d="M367 24v11m0 30v11m-26-26h11m30 0h11" stroke="#ffb042" stroke-linecap="round" />
      <path d="M53 141l47-31" stroke="#38e0ff" stroke-linecap="round" stroke-width="11" />
      <path d="M82 141l13-17 17 17z" fill="#25485a" stroke="#38e0ff" stroke-opacity=".8" />
      <circle cx="91" cy="141" r="13" fill="#0b1628" stroke="#38e0ff" stroke-width="2" />
      <circle cx="91" cy="141" r="4" fill="#38e0ff" fill-opacity=".72" />
      <path d="M54 157h74" stroke="#38e0ff" stroke-opacity=".5" stroke-width="2" />
      <text x="20" y="24" fill="#8297b8" font-family="monospace" font-size="9" letter-spacing="2">CÁLCULO DE TRAYECTORIA</text>
      <text x="333" y="88" fill="#ffcf83" font-family="monospace" font-size="8" letter-spacing="1">OBJETIVO</text>
    </svg>
    <p class="loader-kicker">SISTEMA DE CONTROL · NEWTON–RAPHSON</p>
    <h1>Calculando trayectoria</h1>
    <p class="loader-copy">Calibrando el cañón y preparando el campo de tiro...</p>
    <div class="loader-track" role="progressbar" aria-label="Progreso estimado de carga" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
      <span id="loader-progress-bar"></span>
    </div>
    <div class="loader-status">
      <span id="loader-progress-status">DESCARGANDO EL JUEGO</span>
      <span id="loader-progress-percent" aria-hidden="true">0%</span>
    </div>
  </div>
</div>
<div id="orientation-gate" role="dialog" aria-modal="true" aria-labelledby="orientation-title" aria-hidden="true">
  <div class="orientation-card">
    <svg class="orientation-icon" viewBox="0 0 64 64" aria-hidden="true">
      <rect x="21" y="7" width="22" height="50" rx="4" fill="none" stroke="currentColor" stroke-width="3" />
      <circle cx="32" cy="49" r="1.8" fill="currentColor" />
    </svg>
    <h2 id="orientation-title">Gira tu teléfono</h2>
    <p>Artillery Calculation se juega en pantalla horizontal.</p>
    <p id="orientation-status" aria-live="polite">Intentando activar la orientación horizontal. Si no gira, usa el botón o gira el móvil manualmente.</p>
    <button id="rotate-screen" type="button">Intentar giro automático</button>
  </div>
</div>
<input id="mobile-angle-input" type="text" inputmode="decimal" enterkeyhint="done"
  maxlength="7" autocomplete="off" autocapitalize="off" spellcheck="false"
  aria-label="Ángulo del disparo, de 0 a 180 grados">
<script>
(() => {
  const canvas = document.getElementById("canvas");
  if (!canvas) return;
  const loader = document.getElementById("game-loader");
  const progressBar = document.getElementById("loader-progress-bar");
  const progressTrack = loader.querySelector('[role="progressbar"]');
  const progressStatus = document.getElementById("loader-progress-status");
  const progressPercent = document.getElementById("loader-progress-percent");
  const orientationGate = document.getElementById("orientation-gate");
  const orientationStatus = document.getElementById("orientation-status");
  const rotateButton = document.getElementById("rotate-screen");
  const mobileAngleInput = document.getElementById("mobile-angle-input");
  const portrait = window.matchMedia("(orientation: portrait)");
  const coarsePointer = window.matchMedia("(pointer: coarse)");
  const loadingStartedAt = performance.now();
  let resizeFrame = 0;
  let resizeObserver;
  let downloadCompletedAt = null;
  let displayedProgress = 0;

  const updateLoadingProgress = () => {
    if (document.body.classList.contains("game-ready")) {
      displayedProgress = 100;
      progressStatus.textContent = "JUEGO LISTO";
      progressPercent.textContent = "100%";
      progressTrack.setAttribute("aria-valuenow", "100");
      progressBar.style.width = "100%";
      return;
    }

    const download = document.getElementById("progress");
    const total = download ? Number(download.max) : 0;
    const current = download ? Number(download.value) : 0;
    const fraction = total > 0 ? Math.min(1, Math.max(0, current / total)) : 0;
    const now = performance.now();
    if (fraction >= 1 && downloadCompletedAt === null) downloadCompletedAt = now;
    const downloadProgress = Math.floor(fraction * 80);
    const elapsedEstimate = Math.min(95, Math.floor((now - loadingStartedAt) / 70));
    const preparationProgress = downloadCompletedAt === null
      ? elapsedEstimate
      : Math.min(99, 80 + Math.floor((now - downloadCompletedAt) / 800));
    const progress = Math.max(downloadProgress, preparationProgress);
    progressStatus.textContent = progress >= 75
      ? "PREPARANDO EL JUEGO"
      : "CARGANDO EL MOTOR";
    displayedProgress = Math.max(displayedProgress, progress);
    progressPercent.textContent = `${displayedProgress}%`;
    progressTrack.setAttribute("aria-valuenow", String(displayedProgress));
    progressBar.style.width = `${displayedProgress}%`;
  };

  const isMobilePortrait = () => portrait.matches && coarsePointer.matches;
  const requestLandscape = (enterFullscreen = false) => {
    let fullscreen = Promise.resolve();
    if (enterFullscreen && !document.fullscreenElement && document.documentElement.requestFullscreen) {
      fullscreen = document.documentElement.requestFullscreen().catch(() => {});
    }
    return fullscreen.then(() => {
      const orientation = window.screen && window.screen.orientation;
      if (!orientation || typeof orientation.lock !== "function") return false;
      return orientation.lock("landscape").then(() => true).catch(() => false);
    }).then((locked) => {
      if (!locked && orientationStatus) {
        orientationStatus.textContent = "Este navegador no permite girar la pantalla automáticamente. Activa el giro del móvil y colócalo horizontalmente.";
      }
      return locked;
    });
  };
  const updateOrientation = () => {
    const blocked = isMobilePortrait();
    document.body.classList.toggle("needs-landscape", blocked);
    if (!blocked && orientationGate.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    orientationGate.setAttribute("aria-hidden", String(!blocked));
    if (blocked) requestLandscape();
  };

  const fitCanvas = () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      const viewport = window.visualViewport;
      const width = viewport ? viewport.width : document.documentElement.clientWidth;
      const height = viewport ? viewport.height : document.documentElement.clientHeight;
      if (!width || !height || !canvas.width || !canvas.height) return;
      const scale = Math.min(width / canvas.width, height / canvas.height);
      canvas.style.setProperty("width", `${Math.floor(canvas.width * scale)}px`, "important");
      canvas.style.setProperty("height", `${Math.floor(canvas.height * scale)}px`, "important");
      positionMobileAngleInput();
    });
  };
  const positionMobileAngleInput = () => {
    if (mobileAngleInput.getAttribute("data-editing") !== "true") return;
    const rect = canvas.getBoundingClientRect();
    mobileAngleInput.style.left = `${rect.left + rect.width * 884 / 1280}px`;
    mobileAngleInput.style.top = `${rect.top + rect.height * 294 / 720}px`;
    mobileAngleInput.style.width = `${rect.width * 226 / 1280}px`;
    mobileAngleInput.style.height = `${rect.height * 48 / 720}px`;
  };
  const hideMobileAngleInput = () => {
    mobileAngleInput.setAttribute("data-editing", "false");
    mobileAngleInput.style.display = "none";
    if (document.activeElement === mobileAngleInput) mobileAngleInput.blur();
  };
  canvas.addEventListener("click", (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width * 1280;
    const y = (event.clientY - rect.top) / rect.height * 720;
    if (x >= 884 && x <= 1110 && y >= 294 && y <= 342) {
      mobileAngleInput.setAttribute("data-editing", "true");
      mobileAngleInput.style.display = "block";
      positionMobileAngleInput();
      mobileAngleInput.focus({ preventScroll: true });
    } else {
      hideMobileAngleInput();
    }
  }, true);
  mobileAngleInput.addEventListener("focus", () => {
    mobileAngleInput.setAttribute("data-editing", "true");
  });
  mobileAngleInput.addEventListener("blur", () => {
    mobileAngleInput.setAttribute("data-editing", "false");
    mobileAngleInput.style.display = "none";
  });
  mobileAngleInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      mobileAngleInput.setAttribute("data-submit", "true");
      mobileAngleInput.blur();
    }
  });
  mobileAngleInput.addEventListener("input", positionMobileAngleInput);
  rotateButton.addEventListener("click", () => requestLandscape(true));
  window.addEventListener("resize", fitCanvas, { passive: true });
  window.addEventListener("orientationchange", () => {
    fitCanvas();
    updateOrientation();
  }, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", fitCanvas, { passive: true });
  }
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(fitCanvas);
    resizeObserver.observe(canvas);
  } else if (window.MutationObserver) {
    new MutationObserver(fitCanvas).observe(canvas, {
      attributes: true,
      attributeFilter: ["width", "height"],
    });
  }
  [portrait, coarsePointer].forEach((query) => {
    if (query.addEventListener) {
      query.addEventListener("change", updateOrientation);
    } else if (query.addListener) {
      query.addListener(updateOrientation);
    }
  });
  updateLoadingProgress();
  window.setInterval(updateLoadingProgress, 150);
  fitCanvas();
  updateOrientation();
})();
</script>
"""

if (APP_DIR / "build").exists():
    shutil.rmtree(APP_DIR / "build")
APP_DIR.mkdir(exist_ok=True)

stale_package = APP_DIR / "src"
if stale_package.exists():
    shutil.rmtree(stale_package)

for stale_file in (
    APP_DIR / "main.py",
    APP_DIR / "artillery_calculation.py",
    APP_DIR / "favicon.png",
):
    if stale_file.exists():
        stale_file.unlink()

with tempfile.TemporaryDirectory(prefix="artillery-pygbag-") as temp_dir:
    source_dir = Path(temp_dir)
    shutil.copy2(ROOT / "main.py", source_dir / "main.py")
    shutil.copy2(ROOT / "artillery_calculation.py", source_dir / "artillery_calculation.py")
    shutil.copy2(ROOT / "assets" / "favicon.png", source_dir / "favicon.png")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pygbag",
            "--build",
            "--width",
            "1920",
            "--height",
            "1080",
            "--title",
            "Artillery Calculation",
            "main.py",
        ],
        cwd=source_dir,
        check=True,
    )
    generated_web = source_dir / "build" / "web"
    if not generated_web.is_dir():
        raise FileNotFoundError(f"No se encontró la salida web generada: {generated_web}")
    (APP_DIR / "build").mkdir(parents=True, exist_ok=True)
    shutil.copytree(generated_web, APP_DIR / "build" / "web")

output_path = APP_DIR / "build" / "web" / "index.html"
html = output_path.read_text(encoding="utf-8")
html, width_count = re.subn(
    r"(?m)^WIDTH=\d+\s+# 1920$",
    "WIDTH=1920  # 1920",
    html,
    count=1,
)
html, height_count = re.subn(
    r"(?m)^HEIGHT=\d+\s+# 1080$",
    "HEIGHT=1080  # 1080",
    html,
    count=1,
)
if not width_count or not height_count:
    raise RuntimeError(f"No se encontró la configuración del lienzo Pygbag en: {output_path}")
html = re.sub(r'\s*<meta name="viewport"[^>]*>', "", html, flags=re.IGNORECASE)
html, head_count = re.subn(
    r"<head([^>]*)>",
    r'\g<0>\n<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">',
    html,
    count=1,
    flags=re.IGNORECASE,
)
if not head_count:
    raise RuntimeError(f"No se encontró <head> en la página generada: {output_path}")
html, runtime_count = re.subn(
    r"(?=<script[^>]+src=[\"']https://pygame-web\.github\.io/)",
    '<link rel="preconnect" href="https://pygame-web.github.io" crossorigin>\n'
    '<link rel="dns-prefetch" href="//pygame-web.github.io">\n',
    html,
    count=1,
    flags=re.IGNORECASE,
)
if not runtime_count:
    raise RuntimeError(f"No se encontró el runtime CDN de Pygbag en: {output_path}")
closing_body = "</body>"
if closing_body not in html.lower():
    raise RuntimeError(f"No se encontró </body> en la página generada: {output_path}")
before_body, _, after_body = html.rpartition(closing_body)
output_path.write_text(
    f"{before_body}{MOBILE_ORIENTATION_UI}{closing_body}{after_body}",
    encoding="utf-8",
)
