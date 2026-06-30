# Ripubblicare le modifiche della shell mobile su `main`

Questa guida ti permette di riaprire una Pull Request puntando al ramo `main`
partendo dallo stato attuale del branch `work` presente sul server.

## 1. Allineare `main`

```bash
git fetch origin
git checkout main
git reset --hard origin/main
```

## 2. Creare un ramo dedicato alla PR

Per mantenere separato il lavoro attuale, crea un nuovo branch basato su
`main`:

```bash
git checkout -b feature/mobile-shell
```

## 3. Portare le modifiche dal branch `work`

Se vuoi replicare esattamente l'ultimo stato del branch `work` puoi
riutilizzare il commit `05776d2` con `cherry-pick`:

```bash
git cherry-pick 05776d2
```

In alternativa puoi effettuare un merge completo del ramo:

```bash
git merge work
```

Risolvi eventuali conflitti, verifica il risultato (`npm run build`) e
committa.

## 4. Aggiornare gli asset generati

Assicurati di eseguire la build prima di committare per rigenerare i file in
`frontend/dist/`:

```bash
cd frontend
npm install
npm run build
cd ..
```

## 5. Pubblicare il branch e aprire la PR

```bash
git push -u origin feature/mobile-shell
```

Infine apri la PR da `feature/mobile-shell` verso `main`. In questo modo GitHub
proporrà automaticamente il ramo corretto e potrai riesaminare il diff prima
dell'approvazione.

