import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
def init_firebase():
    # Check if app is already initialized to avoid errors on reload
    if not firebase_admin._apps:
        cred_path = "service_account.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully.")
            return firestore.client()
        else:
            print("❌ Service account file not found. Firebase features will be disabled.")
            return None
    else:
        return firestore.client()

db = init_firebase()

def get_user(user_id):
    if not db: return None
    doc = db.collection('users').document(str(user_id)).get()
    if doc.exists:
        return doc.to_dict()
    return None

def create_user(user_id, username=None):
    if not db: return None
    data = {
        'joined_at': firestore.SERVER_TIMESTAMP,
        'tier': 'free',
        'is_admin': False,
        'username': username
    }
    db.collection('users').document(str(user_id)).set(data)
    return data

def log_request(user_id, link, platform, status):
    if not db: return
    db.collection('logs').add({
        'user_id': user_id,
        'link': link,
        'platform': platform,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'status': status
    })

def check_rate_limit(user_id, tier):
    if not db: return True # Fail open if DB down/missing
    
    # Define limits
    limits = {
        'free': 3,
        'premium': 5,
        'super': 20
    }
    limit = limits.get(tier, 3)

    # Count today's logs
    # Note: simple query, ideally use a composite index for scale, but fine for now
    import datetime
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    docs = db.collection('logs')\
        .where('user_id', '==', user_id)\
        .where('timestamp', '>=', today)\
        .where('status', '==', 'success')\
        .stream()
    
    count = sum(1 for _ in docs)
    return count < limit, count, limit
