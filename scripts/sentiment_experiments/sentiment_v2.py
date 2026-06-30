from transformers import pipeline

def get_sentiment_score_and_label(text):
    if not text or not text.strip():
        return 6, 'neutral', 0.0

    try:
        classifier = pipeline('sentiment-analysis', model='MilaNLProc/feel-it-italian-sentiment')
        res = classifier(text)[0]
        label = res['label']
        conf = res['score']

        # Mapping 1-10 (5 color clusters)
        # Cluster 1 (1-2): Molto Negativo
        # Cluster 2 (3-4): Negativo
        # Cluster 3 (5-6): Neutro
        # Cluster 4 (7-8): Positivo
        # Cluster 5 (9-10): Molto Positivo

        if label == 'positive':
            if conf > 0.8:
                score = 10 # Molto Positivo
            elif conf > 0.6:
                score = 8  # Positivo
            else:
                score = 6  # Neutro/Positivo soft
        else: # negative
            if conf > 0.8:
                score = 2  # Molto Negativo
            elif conf > 0.6:
                score = 4  # Negativo
            else:
                score = 5  # Neutro/Negativo soft

        # Final label normalization for Nuvia
        if score <= 4: final_label = 'negative'
        elif score <= 6: final_label = 'neutral'
        else: final_label = 'positive'

        return score, final_label, conf if label == 'positive' else -conf
    except Exception:
        return 6, 'neutral', 0.0

texts = [
    "Questo resort è pessimo",
    "Mi sono trovato bene",
    "Tutto sommato okay",
    "Da incubo",
    "Senza infamia e senza lode",
    "Posto fantastico, cibo ottimo e personale gentile",
    "Camera piccola e sporca",
    "Colazione decente ma niente di speciale"
]

for t in texts:
    print(f"'{t}': {get_sentiment_score_and_label(t)}")
