# Lista de chequeo para integrar un PR (DC-47)

Mientras Carlos no esté en el repositorio, el ruleset «Proteger main» no exige aprobaciones. Renato revisa cada PR con esta lista antes de fusionarlo. Cuando Carlos vuelva, se evalúa volver a exigir 1 aprobación.

## Antes de abrir el PR

- [ ] La rama sale de `main` (o de la rama anterior de la cadena) y tiene una sola HU o tarea.
- [ ] Los commits siguen Conventional Commits en español, con el scope del área.
- [ ] Las pruebas de la HU están en verde y la cobertura de lo tocado es de al menos 70 %.
- [ ] Ruff, Bandit, ESLint y `tsc` sin errores; el OpenAPI se regenera sin avisos y los tipos de la web están al día.
- [ ] No hay secretos ni datos personales (solo datos sintéticos; `.env` fuera del repositorio).
- [ ] Documentación al día: `docs/evidencias/<HU>/resultados.md`, `docs/avance.md`, `docs/prs/<HU>.md` y el DC si hubo una decisión.

## En el PR

- [ ] Título en Conventional Commits; el cuerpo cierra el issue (`Closes #N`).
- [ ] El check `ci` está en verde con la rama al día con `main`.
- [ ] Las conversaciones están resueltas.

## Al fusionar

- [ ] Fusión *squash*. Mensaje: el título del PR y la lista de HU, DC y CC que incluye.
- [ ] No se borra la rama remota.
- [ ] La tarjeta del tablero pasa a «Hecho» y el plan de fusión registra rama → PR → hash del squash.
