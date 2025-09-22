# iTech - Modular Django Project

iTech is a modular Django application built with a microservices-inspired architecture. It integrates AI-powered recommendation systems and leverages multiple technologies to provide a scalable and modern solution.

## 🌐 Architecture

This project is designed with modularity in mind:

* **Modular Apps:** Each feature is isolated in its own Django app for scalability and maintainability.
* **Dockerized:** All services are containerized using Docker and orchestrated with Docker Compose.
* **Databases:**
  * **PostgreSQL** for relational data.
  * **MongoDB** for document-based storage.
* **Caching:** Redis is used for caching and asynchronous task management.
* **AI & Recommendations:** Integrated AI models provide recommendations and smart content suggestions.

## 🛠️ Technologies

* **Backend:** Django, Django REST Framework
* **Databases:** PostgreSQL, MongoDB
* **Cache:** Redis
* **Containerization:** Docker & Docker Compose
* **AI & ML:** Python-based AI modules for recommendations
* **Task Queue:** Celery (with Redis broker)

## 💾 Getting Started

1. **Clone the repository:**

```bash
git clone https://github.com/MeysamDargin/itech-django.git

cd itech
```

2. **Start services with Docker Compose:**

```bash
docker-compose up --build
```

3. **Access the web app:**

* Backend API: `http://localhost:8001/`

## ⚡ Features

* **User Management:** Signup, login, profiles, roles.
* **Articles:** CRUD operations, summaries, translations.
* **AI Recommendations:** Personalized content suggestions.
* **Notifications:** Real-time alerts.
* **Multi-Database Support:** PostgreSQL + MongoDB.
* **Caching & Queueing:** Redis + Celery for fast performance.


## 📜 License

This project is licensed under the MIT License.
