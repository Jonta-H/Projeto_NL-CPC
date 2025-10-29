from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline; 

tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-large-finetuned-conll03-german")
model = AutoModelForTokenClassification.from_pretrained("xlm-roberta-large-finetuned-conll03-german")
classifier = pipeline(task="ner", model=model, tokenizer=tokenizer)
print(classifier(f'Texto: {input()}'))
