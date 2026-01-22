from classifier import predict_category, classifier_pipeline, CANDIDATE_LABELS

text = "Olá, estou com problemas no pagamento"
result = classifier_pipeline(text, candidate_labels=CANDIDATE_LABELS)

print(f"Texto: '{text}'")
print("Scores Brutos:")
for label, score in zip(result['labels'], result['scores']):
    print(f"  - {label}: {score:.4f}")

print("-" * 30)
final = predict_category(text)
print(f"Classificação Final Atual: {final['categoria']}")
