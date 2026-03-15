FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1

# Create working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "application.api:application", "--host", "0.0.0.0", "--port", "8000"]