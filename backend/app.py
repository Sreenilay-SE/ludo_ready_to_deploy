from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from functools import wraps
import time
import redis
import json
import os
import re
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS with support for file:// origins and custom headers
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Allow all origins to prevent CORS issues
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False,
        "max_age": 3600
    }
})

# Redis connection for session storage
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    print("✅ Redis connection successful")
except Exception as e:
    print(f"⚠️  Redis connection failed: {e}")
    print("⚠️  Falling back to in-memory storage (not recommended for production)")
    redis_client = None

# Rate limiter configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}" if redis_client else "memory://"
)

# API Key from environment
API_KEY = os.getenv('API_KEY', 'exitguard_demo_key_2026')

# JWT Secret Key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'exitguard_jwt_secret_2026_secure_key')

# Demo users (hardcoded for demo purposes)
DEMO_USERS = {
    'admin': {'password': 'admin123', 'role': 'admin'},
    'support': {'password': 'support123', 'role': 'admin'},
    'demo': {'password': 'demo123', 'role': 'user'}
}

# Fallback in-memory storage if Redis fails
sessions_memory = {}

# ============================================================================
# REDIS HELPER FUNCTIONS
# ============================================================================

def store_session_redis(session_id, session_data):
    """Store session in Redis with 5-minute expiry"""
    try:
        if redis_client:
            redis_client.setex(
                f"session:{session_id}",
                300,  # 5 minutes TTL
                json.dumps(session_data)
            )
        else:
            # Fallback to memory
            sessions_memory[session_id] = session_data
    except Exception as e:
        print(f"Error storing session: {e}")
        sessions_memory[session_id] = session_data

def get_session_redis(session_id):
    """Retrieve session from Redis"""
    try:
        if redis_client:
            data = redis_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        else:
            return sessions_memory.get(session_id)
    except Exception as e:
        print(f"Error retrieving session: {e}")
        return sessions_memory.get(session_id)

def get_all_sessions_redis():
    """Get all active sessions from Redis"""
    try:
        if redis_client:
            keys = redis_client.keys("session:*")
            sessions = []
            for key in keys:
                data = redis_client.get(key)
                if data:
                    sessions.append(json.loads(data))
            return sessions
        else:
            return list(sessions_memory.values())
    except Exception as e:
        print(f"Error retrieving all sessions: {e}")
        return list(sessions_memory.values())

# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Include X-API-Key header in your request'
            }), 401
        
        if api_key != API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'Unauthorized access'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_session_id(session_id):
    """Validate session ID format"""
    if not session_id or not isinstance(session_id, str):
        return False
    if len(session_id) > 100:
        return False
    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\-_]+$', session_id):
        return False
    return True

def validate_behavior_data(data):
    """Validate incoming behavior tracking data"""
    required_fields = ['session_id', 'behaviors']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate session ID
    if not validate_session_id(data['session_id']):
        return False, "Invalid session ID format"
    
    # Validate behaviors structure
    behaviors = data['behaviors']
    if not isinstance(behaviors, dict):
        return False, "Behaviors must be an object"
    
    # Validate behavior counts - UPDATED to include mood-related fields
    valid_behaviors = [
        'rageClicks', 'deadClicks', 'hesitations', 'idleTime', 'scrollCount', 'mouseJiggles',
        # NEW: Mood-related behaviors
        'cartRevisits', 'itemAddRemoves', 'scrollDirectionChanges', 'mouseShakeIntensity',
        'priceAreaTime', 'modalToggle', 'tabSwitches', 'mouseExitAttempts',
        'addToCartActions', 'checkoutAttempts'
    ]
    for key, value in behaviors.items():
        if key not in valid_behaviors:
            return False, f"Unknown behavior type: {key}"
        if not isinstance(value, (int, float)) or value < 0:
            return False, f"Invalid value for {key}"
    
    return True, None

def require_jwt_token(f):
    """Decorator to require JWT token for dashboard access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Authorization token required',
                'message': 'Include Authorization header with Bearer token'
            }), 401
        
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            
            # Verify and decode token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            
            # Add user info to request context
            request.user = payload
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expired',
                'message': 'Please login again'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Invalid token',
                'message': 'Authentication failed'
            }), 403
    
    return decorated_function

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ============================================================================
# RISK CALCULATION ALGORITHMS
# ============================================================================

def calculate_churn_risk(behaviors):
    """
    Heuristic scoring algorithm to calculate churn risk (0-100)
    IMPROVED: Requires multiple frustration signals to avoid false positives
    """
    rage_clicks = behaviors.get('rageClicks', 0)
    dead_clicks = behaviors.get('deadClicks', 0)
    idle_time = behaviors.get('idleTime', 0)
    hesitations = behaviors.get('hesitations', 0)
    scroll_count = behaviors.get('scrollCount', 0)
    mouse_jiggles = behaviors.get('mouseJiggles', 0)
    
    # Count clear frustration signals with more sensitive thresholds
    frustration_signals = 0
    
    if rage_clicks >= 2:  # 2+ rapid clicks = frustration (reduced from 3)
        frustration_signals += 1
    if dead_clicks >= 2:  # 2+ dead clicks = UI confusion (reduced from 3)
        frustration_signals += 1
    if hesitations >= 3:  # 3+ long hovers = indecision (reduced from 5)
        frustration_signals += 1
    if idle_time >= 20:  # 20+ seconds idle = distraction (reduced from 30)
        frustration_signals += 1
    if mouse_jiggles >= 6:  # 6+ jiggles = impatience (reduced from 10)
        frustration_signals += 1
    
    # Require at least 2 frustration signals for medium/high risk
    # This prevents false positives from single behaviors
    if frustration_signals < 2:
        return min(20, frustration_signals * 10)  # Low risk (0-20)
    
    # Calculate weighted score with improved weights
    score = (
        rage_clicks * 20 +       # Increased - most reliable frustration signal
        dead_clicks * 10 +       # Decreased - can be accidental
        hesitations * 5 +        # Decreased - normal behavior when reading
        mouse_jiggles * 2 +      # Decreased - some fidgeting is normal
        min(idle_time / 2, 15) * 2  # Capped lower - reading is not frustration
        # Removed scroll_count - scrolling is engagement, not frustration!
    )
    
    # Normalize to 0-100 scale
    risk_score = min(100, int(score))
    
    return risk_score

def identify_root_cause(behaviors):
    """
    Identify the primary cause of churn risk
    """
    rage_clicks = behaviors.get('rageClicks', 0)
    dead_clicks = behaviors.get('deadClicks', 0)
    idle_time = behaviors.get('idleTime', 0)
    hesitations = behaviors.get('hesitations', 0)
    
    causes = []
    
    if rage_clicks >= 2:
        causes.append("High frustration (rage clicks detected)")
    if dead_clicks >= 2:
        causes.append("UI responsiveness issues (dead clicks)")
    if idle_time >= 15:
        causes.append("User confusion or distraction (extended idle)")
    if hesitations >= 3:
        causes.append("Purchase hesitation")
    
    if not causes:
        return "Normal user behavior"
    
    return " + ".join(causes)

def suggest_intervention(risk_score, root_cause):
    """
    Suggest appropriate intervention based on risk level
    """
    if risk_score < 30:
        return "Monitor session - no intervention needed"
    elif risk_score < 60:
        return "Prepare proactive outreach - user showing mild frustration"
    else:
        return "IMMEDIATE INTERVENTION - Trigger discount popup or live chat"

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """
    Login endpoint - authenticates user and returns JWT token
    """
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'error': 'Missing credentials',
                'message': 'Username and password required'
            }), 400
        
        
        # Check credentials against demo users
        if username in DEMO_USERS and DEMO_USERS[username]['password'] == password:
            user_role = DEMO_USERS[username]['role']
            
            # Generate JWT token
            payload = {
                'username': username,
                'role': user_role,
                'exp': datetime.utcnow() + timedelta(hours=24),  # 24 hour expiration
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'token': token,
                'username': username,
                'role': user_role,
                'message': 'Login successful'
            }), 200
        else:
            return jsonify({
                'error': 'Invalid credentials',
                'message': 'Username or password incorrect'
            }), 401
            
    except Exception as e:
        app.logger.error(f"Error in /api/login: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/track', methods=['POST'])

@require_api_key
@limiter.limit("100 per minute")
def track_events():
    """
    Receive tracking events from frontend SDK
    NOW INCLUDES: Customer mood detection data
    """
    try:
        data = request.json
        
        # Validate input data
        is_valid, error_msg = validate_behavior_data(data)
        if not is_valid:
            # Log the validation error for debugging
            print(f"❌ Validation failed: {error_msg}")
            print(f"📦 Received data keys: {data.keys()}")
            print(f"📊 Behaviors: {data.get('behaviors', {})}")
            return jsonify({'error': error_msg}), 400
        
        session_id = data.get('session_id')
        timestamp = data.get('timestamp')
        events = data.get('events', [])
        behaviors = data.get('behaviors', {})
        
        # NEW: Mood detection data
        mood = data.get('mood', 'neutral')
        mood_scores = data.get('moodScores', {})
        mood_confidence = data.get('moodConfidence', 0)
        
        # Get or create session data
        session = get_session_redis(session_id)
        
        if not session:
            session = {
                'session_id': session_id,
                'start_time': timestamp,
                'last_active': timestamp,
                'events': [],
                'behaviors': {
                    'rageClicks': 0,
                    'deadClicks': 0,
                    'idleTime': 0,
                    'hesitations': 0,
                    'scrollCount': 0,
                    'mouseJiggles': 0
                },
                'risk_score': 0,
                'root_cause': 'Normal user behavior',
                'suggested_action': 'Monitor session',
                'intervention_triggered': False,
                'intervention_type': None,
                'intervention_time': None,
                'conversion_status': 'pending',
                'order_value': 0,
                'converted_at': None,
                # NEW: Mood tracking fields
                'mood': 'neutral',
                'mood_scores': {},
                'mood_confidence': 0,
                'mood_history': []
            }
        
        # Update session
        session['last_active'] = timestamp
        session['events'].extend(events)
        
        # Update behavior counts (cumulative)
        for key, value in behaviors.items():
            session['behaviors'][key] = max(session['behaviors'].get(key, 0), value)
        
        # NEW: Update mood data
        if mood != 'neutral' and mood != session.get('mood', 'neutral'):
            # Mood changed - add to history
            if 'mood_history' not in session:
                session['mood_history'] = []
            
            session['mood_history'].append({
                'mood': mood,
                'confidence': mood_confidence,
                'timestamp': timestamp
            })
        
        session['mood'] = mood
        session['mood_scores'] = mood_scores
        session['mood_confidence'] = mood_confidence
        
        # Calculate risk score
        risk_score = calculate_churn_risk(session['behaviors'])
        root_cause = identify_root_cause(session['behaviors'])
        suggested_action = suggest_intervention(risk_score, root_cause)
        
        # Update session with scores
        session['risk_score'] = risk_score
        session['root_cause'] = root_cause
        session['suggested_action'] = suggested_action
        
        # Store updated session in Redis
        store_session_redis(session_id, session)
        
        # Return response
        return jsonify({
            'success': True,
            'session_id': session_id,
            'risk_score': risk_score,
            'root_cause': root_cause,
            'suggested_action': suggested_action,
            'mood': mood  # Echo back mood
        })
    
    except Exception as e:
        app.logger.error(f"Error in /api/track: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/sessions', methods=['GET'])
@require_jwt_token
@limiter.limit("60 per minute")
def get_all_sessions():
    """
    Get all active sessions for dashboard
    NOW INCLUDES: Customer mood analytics
    """
    try:
        # Get all sessions from Redis
        all_sessions = get_all_sessions_redis()
        
        # Filter sessions active in last 5 minutes
        current_time = int(time.time() * 1000)
        active_sessions = []
        
        for session in all_sessions:
            last_active_seconds = (current_time - session['last_active']) / 1000
            
            # Only include sessions active in last 5 minutes
            if last_active_seconds < 300:
                active_sessions.append({
                    'session_id': session['session_id'],
                    'risk_score': session['risk_score'],
                    'root_cause': session['root_cause'],
                    'suggested_action': session['suggested_action'],
                    'last_active': f"{int(last_active_seconds)}s ago",
                    'behaviors': session['behaviors'],
                    # NEW: Mood data
                    'mood': session.get('mood', 'neutral'),
                    'mood_confidence': session.get('mood_confidence', 0),
                    'mood_scores': session.get('mood_scores', {})
                })
        
        # Sort by risk score descending
        active_sessions.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return jsonify({
            'sessions': active_sessions,
            'total_sessions': len(active_sessions),
            'high_risk_count': sum(1 for s in active_sessions if s['risk_score'] >= 60)
        })
    
    except Exception as e:
        app.logger.error(f"Error in /api/sessions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
@require_api_key
@limiter.limit("60 per minute")
def get_session(session_id):
    """
    Get detailed session data
    """
    try:
        if not validate_session_id(session_id):
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        session = get_session_redis(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(session)
    
    except Exception as e:
        app.logger.error(f"Error in /api/session: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/intervention', methods=['POST'])
@require_api_key
@limiter.limit("100 per minute")
def mark_intervention():
    """
    Mark that an intervention was triggered for a session
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        intervention_type = data.get('intervention_type', 'discount_popup')
        timestamp = data.get('timestamp')
        
        if not validate_session_id(session_id):
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Get existing session
        session = get_session_redis(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Mark intervention
        session['intervention_triggered'] = True
        session['intervention_type'] = intervention_type
        session['intervention_time'] = timestamp
        
        # Store updated session
        store_session_redis(session_id, session)
        
        return jsonify({
            'success': True,
            'message': 'Intervention marked successfully'
        })
    
    except Exception as e:
        app.logger.error(f"Error in /api/intervention: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/convert', methods=['POST'])
@require_api_key
@limiter.limit("100 per minute")
def record_conversion():
    """
    Record a purchase/conversion and determine if it was salvaged
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        order_value = data.get('order_value', 0)
        timestamp = data.get('timestamp')
        
        if not validate_session_id(session_id):
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Get existing session
        session = get_session_redis(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Determine if this is a salvaged conversion
        # SALVAGE CRITERIA: High risk (>=60) AND intervention was triggered
        is_salvaged = (session['risk_score'] >= 60 and 
                      session['intervention_triggered'] == True)
        
        # Update session with conversion data
        session['conversion_status'] = 'salvaged' if is_salvaged else 'converted'
        session['order_value'] = order_value
        session['converted_at'] = timestamp
        
        # Store updated session with extended TTL (keep for analytics)
        if redis_client:
            redis_client.setex(
                f"session:{session_id}",
                3600,  # Keep conversions for 1 hour
                json.dumps(session)
            )
        else:
            sessions_memory[session_id] = session
        
        return jsonify({
            'success': True,
            'salvaged': is_salvaged,
            'revenue_saved': order_value if is_salvaged else 0,
            'conversion_status': session['conversion_status']
        })
    
    except Exception as e:
        app.logger.error(f"Error in /api/convert: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/salvage-stats', methods=['GET'])
@require_jwt_token
@limiter.limit("60 per minute")
def get_salvage_stats():
    """
    Calculate and return salvage rate statistics
    CP6 INNOVATION: Tracks rescued customers and revenue saved
    """
    try:
        all_sessions = get_all_sessions_redis()
        
        # Filter for sessions with meaningful data
        high_risk_sessions = [s for s in all_sessions if s.get('risk_score', 0) >= 60]
        salvaged_sessions = [s for s in all_sessions if s.get('conversion_status') == 'salvaged']
        converted_sessions = [s for s in all_sessions if s.get('conversion_status') in ['converted', 'salvaged']]
        
        # Calculate metrics
        total_salvaged = len(salvaged_sessions)
        total_high_risk = len(high_risk_sessions)
        total_conversions = len(converted_sessions)
        
        # Salvage Rate = High-risk conversions / Total high-risk sessions
        salvage_rate = (total_salvaged / total_high_risk) if total_high_risk > 0 else 0
        
        # Revenue Saved = Sum of all salvaged order values
        revenue_saved = sum(s.get('order_value', 0) for s in salvaged_sessions)
        
        # Average salvage value
        avg_salvage_value = (revenue_saved / total_salvaged) if total_salvaged > 0 else 0
        
        # Intervention success rate (same as salvage rate for demo)
        intervention_success_rate = salvage_rate
        
        # Total revenue (all conversions)
        total_revenue = sum(s.get('order_value', 0) for s in converted_sessions)
        
        return jsonify({
            'total_salvaged_customers': total_salvaged,
            'total_revenue_saved': round(revenue_saved, 2),
            'salvage_rate': round(salvage_rate, 4),
            'intervention_success_rate': round(intervention_success_rate, 4),
            'avg_salvage_value': round(avg_salvage_value, 2),
            'total_high_risk': total_high_risk,
            'total_conversions': total_conversions,
            'total_revenue': round(total_revenue, 2),
            'salvaged_sessions': salvaged_sessions
        })
    
    except Exception as e:
        app.logger.error(f"Error in /api/salvage-stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    try:
        # Check Redis connection
        redis_status = 'connected' if redis_client and redis_client.ping() else 'disconnected'
        
        # Get active session count
        all_sessions = get_all_sessions_redis()
        active_count = len([s for s in all_sessions if (int(time.time() * 1000) - s['last_active']) / 1000 < 300])
        
        return jsonify({
            'status': 'healthy',
            'timestamp': int(time.time() * 1000),
            'active_sessions': active_count,
            'redis_status': redis_status,
            'storage_type': 'redis' if redis_client else 'memory'
        })
    except Exception as e:
        return jsonify({
            'status': 'degraded',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*60)
    print("🚀 ExitGuard Backend Server Starting...")
    print("="*60)
    print(f"🔐 API Authentication: {'Enabled' if API_KEY else 'Disabled'}")
    print(f"💾 Storage: {'Redis' if redis_client else 'In-Memory (Fallback)'}")
    print(f"🛡️  Rate Limiting: Enabled (100 req/min)")
    print(f"🔑 API Key: {API_KEY[:20]}...")
    print("="*60)
    print("📊 Dashboard: Open dashboard.html in browser")
    print("🛒 Demo Store: Open demo-store.html in browser")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
