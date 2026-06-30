from transformers import pipeline

def get_sentiment_score_and_label(text):
    if not text or not text.strip():
        return 6, 'neutral', 0.0

    try:
        classifier = pipeline('sentiment-analysis', model='MilaNLProc/feel-it-italian-sentiment')
        res = classifier(text)[0]
        label = res['label']
        conf = res['score']

        # Scale: 1-10
        if label == 'positive':
            # Map 0.5-1.0 to 6-10
            score = 6 + int((conf - 0.5) * 8)
        else: # negative
            # Map 0.5-1.0 to 5-1
            score = 5 - int((conf - 0.5) * 8)

        score = max(1, min(10, score))

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
