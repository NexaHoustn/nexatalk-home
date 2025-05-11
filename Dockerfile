# Offizielles Python-Image als Basis
FROM python:3.11-slim

# Setze Arbeitsverzeichnis
WORKDIR /app

# Kopiere Abhängigkeiten
COPY requirements.txt .

# Installiere Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest der Anwendung
COPY . .

# Exponiere Port (Standard Uvicorn-Port)
EXPOSE 8000

# Starte die App mit Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
