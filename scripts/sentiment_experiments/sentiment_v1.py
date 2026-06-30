from transformers import pipeline

def get_score(text):
    classifier = pipeline('sentiment-analysis', model='MilaNLProc/feel-it-italian-sentiment')
    res = classifier(text)[0]
    label = res['label']
    conf = res['score']

    if label == 'positive':
        # Map 0.5-1.0 to 6-10
        score = 6 + int((conf - 0.5) * 8)
        score = min(10, score)
    else:
        # Map 0.5-1.0 to 5-1
        score = 5 - int((conf - 0.5) * 8)
        score = max(1, score)
    return score, label, conf

texts = ["Ottimo", "Buono", "Normale", "Sufficiente", "Scarso", "Pessimo"]
for t in texts:
    print(f"{t}: {get_score(t)}")
