wsgi_app = "app.main:app"
bind = "127.0.0.1:8080"
workers = 5
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
