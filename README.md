<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&height=240&color=0:070a18,50:38e0ff,100:a082ff&text=ARTILLERY%20CALCULATION&fontColor=ffffff&fontSize=46&fontAlignY=38&desc=Dispara%20con%20matem%C3%A1ticas%20%C2%B7%20Newton-Raphson%20en%20acci%C3%B3n&descAlignY=60&descSize=18&animation=fadeIn" alt="Artillery Calculation" width="100%"/>

<img src="assets/logo.ico" alt="Logo" width="84"/>

<a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3200&pause=900&color=38E0FF&center=true&vCenter=true&width=720&lines=Encuentra+el+%C3%A1ngulo+exacto+del+ca%C3%B1%C3%B3n+%F0%9F%8E%AF;10+rondas+%C2%B7+10+minutos+%C2%B7+cero+margen+de+error;Si+fallas%2C+la+ecuaci%C3%B3n+NO+cambia%3A+itera+y+corrige;Tolerancia+de+diana%3A+%C2%B10.005%C2%B0" alt="Typing SVG"/></a>

<br/>

![Python](https://img.shields.io/badge/Python-Pygame-38e0ff?style=for-the-badge&logo=python&logoColor=white&labelColor=070a18)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Pygbag-a082ff?style=for-the-badge&logo=webassembly&logoColor=white&labelColor=070a18)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-ffffff?style=for-the-badge&logo=vercel&logoColor=white&labelColor=070a18)
![Internet](https://img.shields.io/badge/Requiere-Internet-ffb042?style=for-the-badge&labelColor=070a18)

**Simulador balístico educativo de Métodos Numéricos**
*Mira el blanco, halla el ángulo, aplica Newton-Raphson y no falles.*

[🎮 Jugar](#-c%C3%B3mo-ejecutarlo) · [📐 La matemática](#-la-matem%C3%A1tica-detr%C3%A1s) · [🏆 Puntuación](#-puntuaci%C3%B3n) · [🎈 Globos](#-globos-de-ayuda) · [⌨️ Controles](#%EF%B8%8F-controles)

</div>

---

## 🎯 ¿De qué trata?

**Artillery Calculation** es un juego de puntería donde la fuerza bruta no basta: cada disparo es un problema de **búsqueda de raíces**. El cañón dispara una bala con velocidad fija hacia un blanco (un dron, un radar, un puente, un tanque...) y tú debes encontrar el **ángulo** que hace que la bala pase exactamente por el centro del objetivo.

Para lograrlo, el juego te da una herramienta de las matemáticas reales: el método de **Newton-Raphson**. Una tabla con **3 iteraciones** te muestra cómo converge el ángulo, y una de esas filas guarda la respuesta correcta. ¿Sabrás leerla?

> 💡 El juego conserva su implementación completa en Pygame y se ejecuta en el navegador mediante **Pygbag y WebAssembly**. Vercel sirve el resultado como un sitio estático, sin servidor de juego ni base de datos. El navegador necesita conexión a internet para descargar el runtime WebAssembly.

---

## 🧮 La matemática detrás

La función `f(X)` mide **cuánto falla la bala en altura** al llegar al blanco. Cuando `f(X) = 0`, la bala pasa por el centro. Newton-Raphson corrige el ángulo de prueba paso a paso:

<div align="center">

```
              f(Xₙ)
Xₙ₊₁  =  Xₙ − ───────
              f'(Xₙ)
```

</div>

```mermaid
flowchart LR
    A([🎯 Ver el blanco]) --> B[📋 Leer la tabla<br/>de 3 iteraciones]
    B --> C{¿X casi no<br/>cambia?}
    C -- No --> D[🔁 Aplicar la fórmula<br/>con el X nuevo]
    D --> B
    C -- Sí --> E[⌨️ Escribir el ángulo<br/>con milésimas]
    E --> F((💥 FUEGO))
    F --> G{¿Impacto?}
    G -- Diana ±0.005° --> H[🏅 +100]
    G -- Blanco --> I[✅ +60]
    G -- Falló --> J[⏱️ Penalización<br/>y misma ecuación]
    J --> B
```

### Detalles del modelo

| Concepto | Valor |
|---|---|
| Gravedad | `9.81 m/s²` |
| Rango de ángulo | `0°` a `180°` (el blanco puede estar a tu **izquierda**) |
| Distancia al blanco | `100 m` a `1000 m` |
| Tipos de tiro | **Bajo** y **alto** (la bala cae casi vertical) |
| Tolerancia de diana | **±0.005°** |
| Retos con la misma ecuación | Si fallas, la ecuación **no cambia**: intentas otra vez |

---

## 🗺️ Escenarios

Cada ronda genera un reto distinto con un terreno y un objetivo aleatorios:

| Terreno | Objetivos posibles |
|---|---|
| 🟩 **Plano** | Dron enemigo · Antena de radio · Práctica de tiro · Camión abandonado |
| ⛰️ **Colina** | Radar · Globo vigía · Torre de vigía · Faro enemigo |
| 🕳️ **Valle** | Bodega escondida · Puente enemigo · Campamento · Tanque atascado |
| 🏔️ **Cumbre** | Antena en la cumbre · Nido de águilas · Torre de control · Observatorio |

---

## 🏆 Puntuación

<div align="center">

| Resultado | Puntos | Cómo se logra |
|:---:|:---:|:---|
| 🥇 **DIANA PERFECTA** | **+100** | Error de ángulo ≤ **0.005°** |
| 🎯 **BLANCO TOCADO** | **+60** | La bala impacta el objetivo |
| 😬 **CASI** | 0 | Pasó muy cerca, pero no tocó |
| ❌ **FALLASTE** | 0 | Bala perdida |

**Máximo posible:** `10 rondas × 100 = 1000 puntos`

</div>

Las pistas normales y los fallos reducen el multiplicador de puntos **10 % cada uno**; nunca baja de **20 %**. Una pista gratis obtenida de un globo no reduce el multiplicador. El globo **×2** duplica la puntuación del siguiente acierto.

### ⏱️ Reloj

- La partida dura **10 minutos** y consta de **10 rondas**.
- **Acertar nunca descuenta tiempo.**
- Cada fallo resta tiempo de forma progresiva:

```
1.er fallo → −10 s     2.º fallo → −15 s     3.er fallo → −20 s  ...  (tope: −60 s)
```

---

## 💡 Sistema de pistas y consejos

La **bombilla** o la tecla `Tab` ofrece hasta **7 pistas por ecuación**, una cada **15 segundos**. Revelan información de la tabla de Newton-Raphson, desde una explicación general hasta la fila que contiene la respuesta. Cada pista normal reduce el multiplicador de esa ronda un **10 %**.

Tras varios fallos, el juego también puede mostrar **consejos tácticos** sobre cómo corregir el ángulo o interpretar el reto.

---

## 🎈 Globos de ayuda

Después de **3 o más fallos** pueden aparecer globos. Duran **30 segundos**: atraviesa uno con la bala para activar su bonificación. Pueden aparecer varios:

| Globo | Efecto |
|:---:|:---|
| 🟡 **Doble** | **×2 puntos** en tu próximo acierto |
| 🔵 **Congelar** | Detiene el reloj **20 s**; se acumula hasta **60 s** |
| 🟢 **Tiempo** | Añade **45 s** (el reloj no supera los **10 minutos**) |
| 🟠 **Pista** | Revela una pista **sin reducir el multiplicador** |

Si recoges un globo durante un disparo fallido, se evita la penalización de tiempo de ese fallo.

---

## ⌨️ Controles

| Acción | Mouse / Touch | Teclado |
|---|:---:|:---:|
| Iniciar partida | Botón **▶ Jugar** | `Enter` |
| Disparar | Botón **Disparar** | `Enter` |
| Repetir disparo | Esperar la cuenta atrás de **3 segundos** | — |
| Pedir pista (bombilla) | Icono 💡 | `Tab` |
| Acelerar bala en vuelo (×4) | Haz clic mientras viaja | — |
| Silenciar o activar la música | Botón circular con icono de altavoz |
| Volver al inicio durante la partida | Icono de casa junto al audio |
| Siguiente ecuación | Botón | `Enter` (tras acertar) |
| Volver al menú | Botón **Menú** | `Esc` |
| Guardar puntuación | Botón **Guardar** | `Enter` |
| Alternar pantalla completa en escritorio | — | `F11` |

> 🖥️ En escritorio, el juego inicia en pantalla completa y escala su lienzo para ocupar la pantalla; pulsa `F11` para alternar el modo. En el campo de ángulo se aceptan los números de la fila superior y del teclado numérico, con NumLock activado o desactivado. Durante la partida también aparece un teclado numérico en pantalla: escribe el ángulo con sus teclas, usa **BORRAR** para limpiar el campo y **DISPARAR** para disparar. El icono de teclado, junto al control de audio, lo muestra u oculta; al ocultarlo queda una cinta con el icono para fijar o liberar su posición. Arrástralo desde el encabezado o la cinta para colocarlo en otra zona del juego. 📱 En móviles, el juego se adapta al área visible y conserva su proporción sin ocultar ni solicitar pantalla completa del navegador: sus controles y barras permanecen disponibles y responden al tacto. Toca el campo del nombre en la pantalla principal para abrir el teclado de texto e ingresar tu nombre; el campo del ángulo abre el teclado numérico decimal y acepta valores entre `0°` y `180°`. Si el teléfono está en vertical, **Girar pantalla** solicita el giro automático del dispositivo y, si el navegador no lo permite, rota el juego completo dentro del área visible. También puedes girarlo manualmente. La resolución de renderizado web se ajusta al tamaño, densidad y capacidad estimada del dispositivo, hasta un máximo de 1280×720, y se actualiza al cambiar el área visible. Durante la carga se muestra el progreso de descarga y, después, el avance estimado de preparación hasta que el juego está listo.

El menú principal muestra el **Top 4** de jugadores ordenado por promedio de puntos y un indicador compacto de calidad gráfica en un lateral. Las pestañas permiten consultar las instrucciones y la clasificación completa, o cambiar el ajuste **Bajo / Medio / Alto**. Las instrucciones se pueden desplazar con la rueda del mouse o arrastrando/deslizando dentro del panel. El nivel reduce o activa partículas, brillos y capas animadas; la preferencia se guarda para la próxima visita.

La banda sonora electrónica suave se sintetiza localmente con variaciones aleatorias de tempo, armonía y melodía, y se repite con una transición suave. En navegadores comienza después de la primera interacción, por las restricciones de reproducción automática; se genera por bloques para mantener fluido el juego y, en escritorio, se prepara en segundo plano para no retrasar el menú. El botón circular de tamaño reducido muestra el altavoz con ondas cuando la música está activa y una marca de silencio cuando está apagada. Permite controlar la música desde el menú, la partida y los resultados; la preferencia se guarda en el dispositivo.

Los efectos de impacto se preparan al disparar y suenan en el mismo instante en que termina la trayectoria: tienen tonos diferentes para diana, blanco tocado, casi acierto y fallo lejano. El efecto de casi acierto se activa cuando la bala cae dentro del margen de proximidad del objetivo.

---

## 🏅 Clasificación

Al terminar puedes guardar tu nombre (hasta **14 caracteres**) y competir en el ranking local. Se ordena por **promedio de puntos por partida** y muestra:

`PART.` partidas · `ACIER.` aciertos · `ERR.` errores · `A/E` razón aciertos/errores · `PROM.` promedio

> 🔒 En el navegador, el ranking se guarda en cookies locales: es privado, no usa servidor ni base de datos y **no se comparte** entre dispositivos. Cada nombre se registra **una sola vez**.

---

## 🚀 Cómo ejecutarlo

Para preparar la versión web, usa un entorno virtual para no modificar el Python del sistema:

```bash
python -m venv .venv
# Windows
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe build_web.py
.venv\Scripts\python.exe -m http.server 8000 --directory web_build/build/web
# Abre http://localhost:8000
```

En macOS/Linux, sustituye `.venv\Scripts\python.exe` por `.venv/bin/python`.

También puedes ejecutar la versión de escritorio:

```bash
.venv\Scripts\python.exe main.py
```

### 🌐 Publicar en Vercel

Importa el repositorio en Vercel y conserva la configuración de compilación detectada desde `vercel.json`. El proceso crea un entorno virtual `.vercel-venv` para instalar las dependencias sin modificar el Python administrado por Vercel, ejecuta Pygbag y publica `web_build/build/web` como sitio estático. No se requiere una función backend ni una base de datos.

---

## 📁 Estructura del proyecto

```
📦 artillery-calculation
 ┣ 📜 main.py                   ← punto de entrada para escritorio y web
 ┣ 📜 artillery_calculation.py ← lógica del juego, física, interfaz y animaciones
 ┣ 📜 requirements.txt          ← dependencias de escritorio y compilación web
 ┣ 📜 build_web.py              ← crea un paquete web aislado del guardado local
 ┣ 📜 vercel.json               ← compilación y publicación estática en Vercel
 ┣ 📁 assets/
 ┃ ┣ 🖼️ logo.ico                ← logo del proyecto
 ┃ ┗ 🖼️ favicon.png             ← icono web
 ┣ 📁 save_prof/                ← puntuaciones locales de escritorio
 ┣ 📁 web_build/                ← paquete web generado (no se sube como fuente)
 ┗ 📘 README.md
```

> El punto de entrada es `main.py`. Pygbag compila desde una carpeta temporal y `web_build/` solo conserva los archivos web generados, sin copias duplicadas del código fuente.

---

## 🛠️ Hecho con

- **Pygame y Pygbag/WebAssembly** para conservar el juego y ejecutarlo dentro del navegador.
- **Bucle asíncrono sincronizado con el navegador** para ceder el control entre cuadros y mantener la interfaz fluida.
- **Vercel estático** para publicar los archivos compilados; no hay servidor de partidas.
- **Newton-Raphson** para la derivada numérica y las iteraciones mostradas en la tabla.
- **Escalado adaptable** al tamaño de la ventana y a la densidad de píxeles.

---

## 🎓 Objetivo educativo

Este proyecto muestra de forma lúdica que un método numérico **converge**: cada iteración acerca el valor a la raíz, y el estudiante aprende a **leer una tabla de iteraciones**, reconocer cuándo `X` deja de cambiar y afinar la respuesta con la precisión que exige la tolerancia.

<div align="center">

<br/>

**¿Listo para no fallar?** 🎯

<img src="https://capsule-render.vercel.app/api?type=waving&height=120&color=0:a082ff,50:38e0ff,100:070a18&section=footer" width="100%" alt="footer"/>

</div>
