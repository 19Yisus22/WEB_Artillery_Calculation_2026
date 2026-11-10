# Artillery Calculation (web)

Mismo código Python/pygame del escritorio, compilado a WebAssembly con pygbag.

## Probar en local
    pip install pygbag
    python -m pygbag app        # abre http://localhost:8000

## Desplegar en Vercel (preset "Other")
1. Sube esta carpeta a un repo de GitHub.
2. Vercel -> Add New Project -> importa el repo. Framework Preset: **Other**
   (vercel.json ya trae Install / Build / Output Directory).
3. Deploy.

## Notas
- La primera carga descarga el runtime de Python (unos MB) y pide un clic para iniciar.
- El ranking se guarda en el localStorage del navegador (en escritorio sigue en save_prof/scores.json).
- app/main.py sigue funcionando en escritorio: `python app/main.py`.
