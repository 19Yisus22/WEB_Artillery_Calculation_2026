import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "web_build"
MOBILE_ORIENTATION_UI = """
<style>
canvas {
  touch-action: none;
  -webkit-tap-highlight-color: transparent;
}
#mobile-orientation {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: grid;
  place-items: center;
  padding: max(24px, env(safe-area-inset-top)) max(24px, env(safe-area-inset-right))
    max(24px, env(safe-area-inset-bottom)) max(24px, env(safe-area-inset-left));
  box-sizing: border-box;
  background: rgba(7, 10, 24, 0.97);
  color: #e9eeff;
  font: 16px/1.5 system-ui, sans-serif;
  text-align: center;
}
#mobile-orientation[hidden] {
  display: none;
}
#mobile-orientation section {
  width: min(100%, 380px);
}
#mobile-orientation .orientation-icon {
  margin: 0 0 12px;
  color: #38e0ff;
  font-size: 64px;
  line-height: 1;
}
#mobile-orientation h1 {
  margin: 0 0 10px;
  font-size: 24px;
}
#mobile-orientation p {
  margin: 0 0 18px;
  color: #b7c1e6;
}
#mobile-orientation button {
  min-height: 48px;
  padding: 10px 18px;
  border: 0;
  border-radius: 12px;
  background: #38e0ff;
  color: #070a18;
  font: 700 16px system-ui, sans-serif;
}
#orientation-status {
  min-height: 24px;
  margin-top: 12px !important;
  font-size: 14px;
}
@media (orientation: landscape), (min-width: 901px), (pointer: fine) {
  #mobile-orientation {
    display: none !important;
  }
}
</style>
<div id="mobile-orientation" role="dialog" aria-modal="true" aria-labelledby="orientation-title" hidden>
  <section>
    <div class="orientation-icon" aria-hidden="true">↻</div>
    <h1 id="orientation-title">Gira tu teléfono</h1>
    <p>Este juego se ve y se controla mejor en posición horizontal.</p>
    <button id="orientation-button" type="button">Girar pantalla automáticamente</button>
    <p id="orientation-status" aria-live="polite">Si el navegador no puede girarla, coloca el teléfono de lado.</p>
  </section>
</div>
<script>
(() => {
  const prompt = document.getElementById("mobile-orientation");
  const button = document.getElementById("orientation-button");
  const status = document.getElementById("orientation-status");
  const portraitMobile = window.matchMedia(
    "(orientation: portrait) and (max-width: 900px) and (pointer: coarse)"
  );
  const updatePrompt = () => {
    prompt.hidden = !portraitMobile.matches;
  };
  updatePrompt();
  portraitMobile.addEventListener("change", updatePrompt);
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Solicitando el giro de pantalla...";
    try {
      if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
      if (!screen.orientation || !screen.orientation.lock) {
        throw new Error("La orientación automática no está disponible");
      }
      await screen.orientation.lock("landscape");
      status.textContent = "Giro solicitado. Si no cambia, gira el teléfono manualmente.";
    } catch {
      status.textContent = "El navegador no permite girar automáticamente. Gira el teléfono de lado.";
      button.disabled = false;
    }
  });
})();
</script>
"""

if (APP_DIR / "build").exists():
    shutil.rmtree(APP_DIR / "build")
APP_DIR.mkdir(exist_ok=True)

for filename in ("main.py", "artillery_calculation.py", "favicon.png"):
    shutil.copy2(ROOT / filename, APP_DIR / filename)

subprocess.run(
    [
        sys.executable,
        "-m",
        "pygbag",
        "--build",
        "--title",
        "Artillery Calculation",
        "main.py",
    ],
    cwd=APP_DIR,
    check=True,
)

output_path = APP_DIR / "build" / "web" / "index.html"
html = output_path.read_text(encoding="utf-8")
closing_body = "</body>"
if closing_body not in html.lower():
    raise RuntimeError(f"No se encontró </body> en la página generada: {output_path}")
before_body, _, after_body = html.rpartition(closing_body)
output_path.write_text(
    f"{before_body}{MOBILE_ORIENTATION_UI}{closing_body}{after_body}",
    encoding="utf-8",
)
