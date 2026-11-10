# Artillery Calculation

Videojuego 2D de precisión matemática hecho con Python y pygame. Eres un artillero que debe hallar el **ángulo de disparo exacto** para dar en el blanco, resolviendo la ecuación con el **método de Newton-Raphson**.

Funciona en el navegador (WebAssembly con pygbag) y también en escritorio. No usa base de datos ni servidor.

## Cómo se juega

1. **Mira el blanco.** Puede estar cerca o lejos (de 100 a 1000 m), arriba o abajo, a tu derecha o a tu izquierda.
2. **Busca el ángulo X.** Escribe el ángulo del cañón en grados, de 0° a 180°: 0° es a la derecha, 90° hacia arriba y 180° a la izquierda.
3. **Usa Newton-Raphson.** Cada ecuación trae su función `f(X)`, su derivada `f'(X)` y una semilla `X0`. La fórmula de iteración es:

   ```
   X(n+1) = X(n) - f(X(n)) / f'(X(n))
   ```

   Repítela hasta que `X(n)` ya no cambie en los 3 decimales. Ese valor es tu ángulo.
4. **Dispara** con el botón o con Enter. Si aciertas aparece "Nueva Ecuación"; si no, la ecuación se mantiene y vuelves a intentarlo.

## Puntuación

| Resultado | Puntos |
|---|---|
| Diana exacta (error de máximo 0.005° respecto a la raíz) | 100 |
| Tocar el blanco sin ser exacto | 60 |
| Fallo | 0 |

Cada pista usada y cada intento fallido reducen un poco el multiplicador de puntos (mínimo ×0.20).

## Tiempo

- Cada partida tiene **10 minutos** y consta de **10 ecuaciones**.
- Cada desacierto **resta tiempo**: empieza en 10 s y va aumentando con los fallos seguidos. Se reinicia al pasar a una nueva ecuación o al empezar otra partida.
- Si el tiempo llega a 0, la partida termina y pasas a la tabla de resultados.
- Tras un acierto, "Nueva Ecuación" aparece sola. Si no la pulsas, la siguiente ecuación empieza automáticamente a los **7 segundos**.

## Ayudas

- **Bombilla de pistas:** hasta 7 pistas por ecuación, una disponible cada 15 s. Cada pista descubre celdas de la tabla de iteraciones y resta puntos.
- **Globos de ayuda:** tras 3 o más desaciertos aparecen globos en el campo, con aviso en pantalla. Revienta uno con un clic o un toque para recibir su ayuda:
  - **Doble:** duplica los puntos.
  - **Congelar:** detiene el tiempo.
  - **Tiempo:** suma segundos.
  - **Pista:** regala una pista nueva.

## Ranking

Al terminar, escribe tu nombre y pulsa **Guardar**.

- Se guarda **un solo registro por partida**: el botón se bloquea y no se duplican puntos.
- Si el nombre ya está registrado, el juego pide uno nuevo.
- La tabla muestra partidas, aciertos, errores, A/E (aciertos entre errores) y el promedio de puntos.

En la web el ranking se guarda en el `localStorage` de tu navegador, así que solo lo ves tú en ese navegador. En escritorio se guarda en `save_prof/scores.json`, junto al juego.

## Controles

| Acción | Control |
|---|---|
| Escribir el ángulo | Teclado numérico (admite punto o coma) |
| Disparar | Enter o botón "Disparar" |
| Pedir pista | Bombilla o tecla Tab |
| Reventar un globo | Clic o toque |
| Pantalla completa (escritorio) | F11 |
| Volver al menú | Esc |

## Pantalla

La resolución se ajusta sola al tamaño de la ventana del navegador o del monitor, con un mínimo de 1280×720, y se reajusta si la redimensionas.

## Ejecutar en escritorio

Requisitos: Python 3.9 o superior.

```
pip install pygame
python main.py
```

## Publicar en la web (Vercel)

1. Sube el contenido de esta carpeta a un repositorio de GitHub. `main.py` debe quedar en la raíz.
2. En [vercel.com](https://vercel.com) elige **Add New → Project**, importa el repo y pulsa **Deploy**. `vercel.json` ya trae el comando de build (pygbag).

Para compilar a mano:

```
pip install pygbag
python -m pygbag --build .
```

Despliega después la carpeta `build/web`. Para probarlo en local, usa `python -m pygbag .` y abre `http://localhost:8000`.

## Estructura

```
main.py          código del juego
vercel.json      configuración de build para Vercel
assets/fonts/    fuentes incluidas (Roboto y DejaVu Sans Mono)
.gitignore       evita subir build/, save_prof/ y caché
```

## Notas

- La primera carga en la web puede tardar unos segundos mientras el navegador descarga el motor de Python.
- Las fuentes Roboto y DejaVu Sans Mono se distribuyen con sus propias licencias libres.
