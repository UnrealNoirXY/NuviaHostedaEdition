# Come Nascondere il Sito ai Motori di Ricerca

Per impedire temporaneamente ai motori di ricerca (come Google, Bing, etc.) di indicizzare il tuo sito, puoi utilizzare principalmente due metodi. Si consiglia di usarli entrambi per la massima efficacia.

---

## Metodo 1: Creare un file `robots.txt`

Il file `robots.txt` è un file di testo che va inserito nella cartella principale (root) del tuo sito. Questo file dà istruzioni ai crawler (i "robot" dei motori di ricerca) su quali pagine possono o non possono visitare.

**Procedura:**

1.  Crea un nuovo file e chiamalo `robots.txt`.
2.  Inserisci al suo interno il seguente testo:

    ```
    User-agent: *
    Disallow: /
    ```

3.  Carica questo file nella directory principale del tuo sito web.

**Spiegazione:**
*   `User-agent: *`: Questa riga indica che le istruzioni sono valide per tutti i motori di ricerca.
*   `Disallow: /`: Questa riga dice ai motori di ricerca di non visitare nessuna pagina del sito (il simbolo `/` rappresenta la radice del sito).

**Nota:** Questo metodo è un'indicazione, ma i motori di ricerca più importanti (Google, Bing, etc.) la rispettano sempre.

---

## Metodo 2: Aggiungere un Meta Tag "noindex" alle Pagine HTML

Questo metodo è più diretto e potente del `robots.txt`. Consiste nell'aggiungere un tag specifico nella sezione `<head>` di ogni pagina HTML che non vuoi indicizzare.

**Procedura:**

1.  Apri i file HTML del tuo sito. Se usi un template di base (come `base.html` in Django o un `header.php` in WordPress), ti basterà modificare solo quel file.
2.  All'interno della sezione `<head>`, aggiungi la seguente riga:

    ```html
    <meta name="robots" content="noindex, nofollow">
    ```

**Spiegazione:**
*   `noindex`: Dice esplicitamente al motore di ricerca di non indicizzare questa pagina.
*   `nofollow`: Dice al motore di ricerca di non seguire i link presenti in questa pagina.

**Vantaggio:** A differenza di `robots.txt`, questo è un comando diretto e non una semplice direttiva. Se una pagina è già stata indicizzata, questo tag farà in modo che venga rimossa dall'indice alla successiva visita del crawler.

---

## Raccomandazione

Per essere sicuro che il sito non venga indicizzato, **si consiglia di implementare entrambi i metodi**. In questo modo, anche se un crawler dovesse per qualche motivo ignorare il `robots.txt`, troverà comunque il tag `noindex` nella pagina.

**Importante:** Ricordati di rimuovere queste modifiche quando sarai pronto a rendere di nuovo il sito visibile ai motori di ricerca!
