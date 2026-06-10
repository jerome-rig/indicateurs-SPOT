# Notes de déploiement — Indicateurs SPOT

## Architecture

- **Code** : dépôt GitHub public `jerome-rig/indicateurs-SPOT`
- **Données** : fichier Excel hébergé dans les Releases GitHub (non indexé publiquement)
- **App en ligne** : Streamlit Community Cloud

---

## Mettre à jour le code (main.py)

```powershell
git add main.py
git commit -m "description de la modification"
git push
```

Streamlit redéploie automatiquement après le push.

---

## Mettre à jour le fichier Excel

1. Va sur **github.com/jerome-rig/indicateurs-SPOT/releases**
2. Clique **Draft a new release**
3. Crée un nouveau tag (ex. `v2.0`)
4. Attache le nouveau fichier Excel
5. Clique **Publish release**
6. Fais un clic droit sur le fichier → **Copier l'adresse du lien**
7. Dans `main.py`, remplace l'URL dans `charger_donnees()` :
   ```python
   url = "NOUVELLE_URL_ICI"
   ```
8. Pousse la modification :
   ```powershell
   git add main.py
   git commit -m "mise à jour fichier Excel vX.0"
   git push
   ```

---

## Partager l'app

L'URL de l'app est disponible sur **share.streamlit.io**.  
Elle est accessible depuis n'importe quel navigateur sans installation.

---

## Restreindre l'accès à certaines personnes

1. Va sur **share.streamlit.io**
2. Clique sur **...** à côté de l'app → **Settings**
3. Onglet **Sharing** → **Only specific people can view this app**
4. Ajoute les adresses email autorisées

Les invités devront se connecter avec un compte Google ou GitHub.  
⚠️ Limite du plan gratuit : **5 personnes maximum**.
