# Proposta per la Funzionalità di Manutenzione

Questo documento descrive la proposta tecnica per implementare la modalità "manutenzione" e presenta alcune idee creative per la pagina che verrà mostrata agli utenti durante questo periodo.

---

## 1. Analisi Tecnica e Implementazione

L'obiettivo è creare una funzionalità che consenta solo a un utente con ruolo `Superadmin` di mettere il sito in modalità manutenzione, bloccando l'accesso a tutti gli altri utenti e mostrando loro una pagina dedicata.

L'implementazione seguirà questi passi:

### a. Modello Dati (`core/models.py`)

Per gestire lo stato di manutenzione in modo persistente, propongo di aggiungere un nuovo modello all'app `core`. Questo modello sarà un "singleton", ovvero ne esisterà una sola istanza, che conterrà tutte le impostazioni globali del sito.

```python
# In core/models.py

class SiteSettings(models.Model):
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Attiva Modalità Manutenzione",
        help_text="Se attivata, solo i Superadmin potranno accedere al sito. Tutti gli altri utenti verranno reindirizzati a una pagina di manutenzione."
    )
    # In futuro, potremmo aggiungere qui un campo per un messaggio di manutenzione personalizzato.

    def __str__(self):
        return "Impostazioni del Sito"

    class Meta:
        verbose_name_plural = "Impostazioni del Sito"

```

### b. Pannello di Controllo per il Superadmin (`core/admin.py`)

Per permettere al Superadmin di attivare/disattivare la modalità, creerò un'interfaccia nel pannello di amministrazione di Django.

*   Registrerò il modello `SiteSettings` nell'admin.
*   Personalizzerò la vista per garantire che solo gli utenti con ruolo `Superadmin` possano visualizzare e modificare questa impostazione.
*   L'interfaccia sarà un semplice interruttore (checkbox) chiaro e facile da usare.

### c. Middleware di Manutenzione (`core/middleware.py`)

Il cuore della logica risiederà in un nuovo middleware.

*   Creerò la classe `MaintenanceModeMiddleware` e la aggiungerò al file `settings.py`.
*   Questo middleware controllerà ogni richiesta in ingresso:
    1.  Verificherà se la modalità manutenzione è attiva.
    2.  Se è attiva, controllerà se l'utente è autenticato e ha il ruolo `Superadmin`.
    3.  **Se l'utente non è un Superadmin**, verrà reindirizzato alla pagina di manutenzione.
    4.  **Se l'utente è un Superadmin**, potrà navigare liberamente nel sito per effettuare controlli.
*   Il middleware escluderà automaticamente gli URL necessari per il suo funzionamento (es. la pagina di login dell'admin, la pagina di manutenzione stessa e i file statici) per evitare reindirizzamenti infiniti.

### d. Pagina di Manutenzione (`core/views.py` e `templates/core/maintenance.html`)

Creerò una vista e un template dedicati per la pagina di manutenzione. Questa pagina sarà "stand-alone" per non dipendere da altre parti del sito che potrebbero essere in fase di aggiornamento.

---

## 2. Idee Creative per la Pagina di Manutenzione

La pagina di manutenzione non deve essere un vicolo cieco, ma un'occasione per comunicare con l'utente in modo originale e in linea con il brand "Noir".

### Idea 1: "Modalità Noir: Indagine in Corso" (Tema Investigativo)

*   **Visual:** Immagina una scrivania da detective in un ufficio buio, illuminata solo da una lampada. Sulla scrivania: una lente d'ingrandimento, un fascicolo "TOP SECRET", una tazza di caffè fumante. Fuori dalla finestra, un'animazione di pioggia battente.
*   **Interattività:**
    *   Cliccando sulla lente d'ingrandimento, l'utente "scopre" un indizio: un messaggio simpatico come "Il bug ha le ore contate" o "Stiamo seguendo una pista promettente".
    *   **Easter Egg:** Un piccolo puzzle o un oggetto da trovare nella scena che, se cliccato, rivela un messaggio di ringraziamento per la pazienza.
*   **Messaggio:** *"Shhh... I nostri migliori detective sono al lavoro. Stiamo indagando per risolvere un caso e migliorare la piattaforma. Torna tra poco per scoprire le novità."*

### Idea 2: "Pit-Stop Tecnico" (Tema Futuristico/Robotico)

*   **Visual:** Un'animazione di piccoli e simpatici robot che si prendono una "pausa caffè" (bevendo olio da una tazzina), mentre un robot più grande lavora in background su un motore complesso.
*   **Interattività:**
    *   Un mini-gioco arcade in stile retrò, come "Schiaccia i Bug!", dove l'utente può passare il tempo cercando di ottenere un punteggio alto.
    *   Al passaggio del mouse, i robot potrebbero salutare o mostrare fumetti con messaggi divertenti.
*   **Messaggio:** *"Anche i nostri instancabili robot hanno bisogno di una pausa! Stiamo facendo un pit-stop tecnico per rendere tutto più veloce e potente. Il tempo di un caffè e saremo di nuovo da te."*

### Idea 3: "Stiamo Affinando gli Ingranaggi" (Tema Elegante e Meccanico)

*   **Visual:** Un design minimalista e scuro, con un'animazione fluida e ipnotica di ingranaggi di precisione (color bronzo o argento) che ruotano lentamente e si incastrano tra loro.
*   **Interattività:** Al passaggio del mouse, gli ingranaggi potrebbero accelerare leggermente o illuminarsi, mostrando la cura e l'attenzione ai dettagli.
*   **Messaggio:** *"La perfezione richiede tempo. Siamo momentaneamente in manutenzione per affinare ogni dettaglio e migliorare la tua esperienza. Torneremo online a breve, più performanti di prima."*

---

Attendo un tuo feedback su quale approccio creativo preferisci e sulla validità della soluzione tecnica proposta prima di procedere.
