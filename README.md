## **Backend README (Django & Channels)**

### **Prerequisites**
Before running the backend, ensure you have the following installed:
- **Python 3.10+** (Recommended)
- **PostgreSQL** (or SQLite for local development)
- **Redis** (Required for WebSocket message queues)
- **Pipenv** or **Virtualenv** (Optional but recommended)
- **Node.js** (For managing WebSockets via Django Channels)

---

### **Setting Up the Backend**

#### **1️1 Clone the Repository**
```bash
git clone https://github.com/supersonicwisd1/home-backend.git
cd home-backend
```

#### **2️. Create a Virtual Environment**
Using **venv**:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

#### **3️. Install Dependencies**
```bash
pip install -r requirements.txt
```

#### **4️. Configure Environment Variables**
Create a **`.env`** file in the root directory:
```bash
touch .env
```
Then, add the following variables:
```ini
# Database
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/chat_db

# Django
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Channels & WebSockets
REDIS_URL=redis://localhost:6379/1
```

#### **5️. Run Migrations**
```bash
python manage.py migrate
```

#### **6️. Create a Superuser (Optional)**
```bash
python manage.py createsuperuser
```

#### **7️. Start Redis**
Add in the Redis url:
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1") 

Uncomment this code on home/settings:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL], 
        },
    },
}
```
Comment this code on home/settings:
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",  # Change to Redis in production
    },
}
```
Make sure Redis is installed and running:
```bash
redis-server
```
Check if Redis is running:
```bash
redis-cli ping
```
It should return:
```
PONG
```

#### **8. Run the Development Server**
```bash
python manage.py runserver
```
If using **Daphne** for WebSockets:
```bash
daphne -b 0.0.0.0 -p 8000 irate.asgi:application
```

---

### ** API Endpoints**
You can now access the API at:
```
http://127.0.0.1:8000/docs/
```
- **Login:** `POST /auth/login/`
- **Register:** `POST /auth/register/`
- **Chat Messages:** `GET /messaging/messages/`
- **Send Message:** `POST /messaging/messages/`
- **WebSocket URL:** `ws://127.0.0.1:8000/ws/chat/`